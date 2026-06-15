# Release Checklist

1. Update version notes in the GitHub release description.
2. Build the Windows executable:

   ```powershell
   .\scripts\build_exe.ps1
   ```

3. Test `dist\FishReader.exe` locally.
4. Create a GitHub release, for example `v0.1.0`.
5. Upload `dist\FishReader.exe` as a release asset.

## Suggested Release Notes

### FishReader v0.1.0

Initial public release.

- Lightweight transparent TXT reader for Windows.
- Adjustable font, text color, text opacity, background color, and background opacity.
- Compact adaptive toolbar with a "More" menu on small windows.
- Remember last file, window geometry, and reading progress.
- Percent-based progress jump.
- Custom shortcuts and Windows global minimize hotkey.
