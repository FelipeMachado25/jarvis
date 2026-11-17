//! Voz para la pestaña JARVIS · Voz.
//!
//! - `voice_say` / `voice_stop`: voz nativa de macOS (`/usr/bin/say`), por si el
//!   WebView no expone `speechSynthesis`.
//! - `voice_transcribe`: audio grabado en la pestaña → Whisper local
//!   (`ffmpeg` + `whisper-cli` de whisper.cpp). El audio nunca sale de la Mac.
//!
//! Sin dependencias nuevas: solo `std` y `tauri`.

use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;

static SPEAKING: Mutex<Option<Child>> = Mutex::new(None);

/// Las apps abiertas desde Finder no heredan el PATH de la terminal.
fn find_bin(name: &str) -> Option<PathBuf> {
    let mut dirs: Vec<PathBuf> = ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin"]
        .iter()
        .map(PathBuf::from)
        .collect();
    if let Ok(path) = std::env::var("PATH") {
        dirs.extend(std::env::split_paths(&path));
    }
    dirs.into_iter().map(|d| d.join(name)).find(|p| p.is_file())
}

fn home() -> PathBuf {
    std::env::var_os("HOME").map(PathBuf::from).unwrap_or_else(|| PathBuf::from("/tmp"))
}

#[tauri::command]
pub async fn voice_say(text: String, lang: Option<String>) -> Result<(), String> {
    voice_stop();
    let voice = match lang.as_deref() {
        Some("en") => std::env::var("JARVIS_VOICE_EN").unwrap_or_else(|_| "Samantha".into()),
        _ => std::env::var("JARVIS_VOICE_ES").unwrap_or_else(|_| "Paulina".into()),
    };
    let child = Command::new("/usr/bin/say")
        .args(["-v", &voice, "-r", "195", &text])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|e| format!("No pude usar `say`: {e}"))?;
    let pid = child.id();
    *SPEAKING.lock().map_err(|e| e.to_string())? = Some(child);
    // Esperar a que termine sin bloquear el hilo principal
    tauri::async_runtime::spawn_blocking(move || loop {
        let mut guard = match SPEAKING.lock() {
            Ok(g) => g,
            Err(_) => return,
        };
        match guard.as_mut() {
            Some(c) if c.id() == pid => {
                if let Ok(Some(_)) = c.try_wait() {
                    *guard = None;
                    return;
                }
            }
            _ => return, // la detuvieron o empezó otra frase
        }
        drop(guard);
        std::thread::sleep(std::time::Duration::from_millis(120));
    })
    .await
    .map_err(|e| e.to_string())
}

#[tauri::command]
pub fn voice_stop() {
    if let Ok(mut guard) = SPEAKING.lock() {
        if let Some(mut c) = guard.take() {
            let _ = c.kill();
            let _ = c.wait();
        }
    }
}

fn b64_decode(input: &str) -> Result<Vec<u8>, String> {
    fn val(c: u8) -> Option<u32> {
        match c {
            b'A'..=b'Z' => Some((c - b'A') as u32),
            b'a'..=b'z' => Some((c - b'a' + 26) as u32),
            b'0'..=b'9' => Some((c - b'0' + 52) as u32),
            b'+' | b'-' => Some(62),
            b'/' | b'_' => Some(63),
            _ => None,
        }
    }
    let mut out = Vec::with_capacity(input.len() * 3 / 4);
    let (mut acc, mut bits) = (0u32, 0u32);
    for &c in input.as_bytes() {
        if c == b'=' || c.is_ascii_whitespace() {
            continue;
        }
        acc = (acc << 6) | val(c).ok_or("audio base64 inválido")?;
        bits += 6;
        if bits >= 8 {
            bits -= 8;
            out.push((acc >> bits) as u8);
            acc &= (1 << bits) - 1;
        }
    }
    Ok(out)
}

fn whisper_model() -> Option<PathBuf> {
    if let Ok(p) = std::env::var("JARVIS_WHISPER_MODEL") {
        return Some(PathBuf::from(p)).filter(|p| p.is_file());
    }
    let dir = home().join(".jarvis").join("models");
    ["ggml-large-v3-turbo.bin", "ggml-medium.bin", "ggml-small.bin", "ggml-base.bin"]
        .iter()
        .map(|n| dir.join(n))
        .find(|p| p.is_file())
}

fn run(cmd: &Path, args: &[&str]) -> Result<(), String> {
    let out = Command::new(cmd).args(args).output().map_err(|e| e.to_string())?;
    if out.status.success() {
        Ok(())
    } else {
        Err(String::from_utf8_lossy(&out.stderr).lines().last().unwrap_or("falló").to_string())
    }
}

#[tauri::command]
pub async fn voice_transcribe(audio_b64: String, mime: Option<String>) -> Result<String, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let ffmpeg = find_bin("ffmpeg").ok_or("Falta ffmpeg: brew install ffmpeg")?;
        let whisper = find_bin("whisper-cli")
            .or_else(|| find_bin("whisper-cpp"))
            .ok_or("Falta whisper.cpp: brew install whisper-cpp")?;
        let model = whisper_model().ok_or(
            "Falta el modelo de Whisper en ~/.jarvis/models (ver INTEGRAR.md)",
        )?;

        let ext = match mime.as_deref().unwrap_or("") {
            m if m.contains("mp4") => "m4a",
            m if m.contains("ogg") => "ogg",
            m if m.contains("wav") => "wav",
            _ => "webm",
        };
        let dir = std::env::temp_dir().join(format!("jarvis-voz-{}", std::process::id()));
        std::fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
        let input = dir.join(format!("in.{ext}"));
        let wav = dir.join("in.wav");
        let out_base = dir.join("out");
        std::fs::write(&input, b64_decode(&audio_b64)?).map_err(|e| e.to_string())?;

        let result = (|| {
            run(&ffmpeg, &["-y", "-loglevel", "error", "-i", input.to_str().unwrap(),
                           "-ar", "16000", "-ac", "1", wav.to_str().unwrap()])?;
            run(&whisper, &["-m", model.to_str().unwrap(), "-f", wav.to_str().unwrap(),
                            "-l", "auto", "-nt", "-otxt", "-of", out_base.to_str().unwrap()])?;
            std::fs::read_to_string(out_base.with_extension("txt"))
                .map(|t| t.split_whitespace().collect::<Vec<_>>().join(" "))
                .map_err(|e| e.to_string())
        })();
        let _ = std::fs::remove_dir_all(&dir);
        result
    })
    .await
    .map_err(|e| e.to_string())?
}

#[cfg(test)]
mod tests {
    use super::b64_decode;

    #[test]
    fn decodes_base64() {
        assert_eq!(b64_decode("SGV5IEphcnZpcw==").unwrap(), b"Hey Jarvis");
        assert_eq!(b64_decode("YQ").unwrap(), b"a");
        assert!(b64_decode("@@").is_err());
    }
}
