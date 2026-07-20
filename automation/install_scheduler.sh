#!/bin/bash
# Instala el scheduler de macOS (launchd): briefing todos los domingos 20:00.
# launchd es lo nativo en macOS (mejor que cron: sobrevive reinicios y sleep).

PLIST="$HOME/Library/LaunchAgents/com.felipe.jarvis.weekly.plist"
mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.felipe.jarvis.weekly</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$HOME/Jarvis/automation/trigger.sh</string>
        <string>weekly</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key><integer>0</integer>
        <key>Hour</key><integer>20</integer>
        <key>Minute</key><integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>$HOME/.jarvis/logs/launchd.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/.jarvis/logs/launchd.log</string>
</dict>
</plist>
EOF

launchctl unload "$PLIST" 2>/dev/null
launchctl load "$PLIST" && echo "✅ Scheduler instalado: domingos 20:00 → briefing semanal."
