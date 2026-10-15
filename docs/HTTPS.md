# Private HTTPS and certificate trust

This guide covers a host running the Python app and clients opening it in a browser. The host stays private: Caddy binds a chosen LAN IPv4 address, checks source subnets, and forwards to the app at `127.0.0.1:8765`. The app password still applies.

## 1. Choose your host address and allowed networks

Reserve a stable private address for the host in your router. Find it in the OS network settings, or with `ip -4 addr` (Linux) / `ipconfig` (Windows). Use your actual address, subnet and optional VPN subnet. Examples below use `192.168.1.50` and `192.168.1.0/24`; replace them throughout.

Permit TCP **9443** through the host firewall only from your chosen LAN/VPN subnets. This project does not change the firewall. Do not expose backend **8765**, forward these ports through the router, or place this single-user application behind a public tunnel. A VPN client needs a route to the host's LAN address. A source allowlist is not a substitute for avoiding public exposure; a proxy/router may mask original source addresses.

## 2A. Linux installed service

After `bash install.sh`, run:

```bash
"$HOME/.local/lib/mystical-mark-studio/current/.venv/bin/python" "$HOME/.local/lib/mystical-mark-studio/current/manage.py" lan
```

Enter your host's private IPv4 address and the allowed LAN/VPN CIDRs when prompted. These must be your actual network values. Caddy must already be installed. The helper writes the private Caddyfile in Studio's data directory and starts `mystical-mark-https.service`. Existing installations that already use HTTPS do not need to rerun this after updating.

## 2B. Portable host: Windows, macOS or manual Linux

Install Caddy from its [official instructions](https://caddyserver.com/docs/install). Keep it and Studio under your normal account. Stop Studio before reconfiguring.

On Windows, from the source folder:

```powershell
.\.venv\Scripts\python.exe manage.py lan --manual
```

On macOS/Linux, from the source folder:

```bash
.venv/bin/python manage.py lan --manual
```

Enter your host's private IPv4 address and allowed client CIDRs. The command prints the private Caddyfile path. Start Studio with `run.py` again. In a second terminal, replace `/absolute/path/to/Caddyfile` below with that printed path (keep quotes around paths containing spaces):

```bash
caddy validate --config "/absolute/path/to/Caddyfile" --adapter caddyfile
caddy run --config "/absolute/path/to/Caddyfile" --adapter caddyfile
```

Keep both terminals open. Open `https://192.168.1.50:9443`, substituting your actual address, after completing certificate trust. Use that HTTPS URL even on the host: Secure login cookies are enabled. This helper does not configure automatic launch on Windows/macOS.

## 3. Locate the root certificate on the host

Caddy generates its local CA when the gateway provisions successfully. Use the CA belonging to the **same Caddy account/storage directory that serves this app**. Do not create a fresh CA on each client.

| Host configuration | Root certificate |
|---|---|
| Linux helper | `~/.local/share/caddy/pki/authorities/local/root.crt` |
| Portable default Caddy | `<Caddy AppDataDir>/pki/authorities/local/root.crt` |

For portable Caddy, run `caddy environ` as the same user and find `caddy.AppDataDir`. It is commonly under `%APPDATA%\Caddy` on Windows, `~/Library/Application Support/Caddy` on macOS, or `~/.local/share/caddy` on Linux, but use the actual reported directory. Do not publish the full environment output; it may contain unrelated secrets.

Copy only **root.crt** to each device through a trusted local transfer. Never transfer `root.key`, intermediate private keys or the entire Caddy data directory. A CA grants trust beyond one URL, so install only a root you control and remove it when no longer needed.

Optionally compare SHA-256 file hashes on both ends to confirm the certificate was transferred intact. Browsers can display certificate fingerprints as well. Visit the exact IP configured in Caddy; using a different IP or hostname can cause a name mismatch even when the root is trusted.

## 4. Trust the root on each client

Menu labels can change by OS/browser version. Managed devices may require an administrator. Installing a certificate and enabling trust are sometimes separate steps.

### iPhone and iPad

1. Transfer/open `root.crt` on the device, then allow the profile download if prompted.
2. Open Settings and install the downloaded profile (usually **Profile Downloaded** or **General → VPN & Device Management**). Review its identity and enter your device passcode when asked.
3. Open **Settings → General → About → Certificate Trust Settings**. Enable full trust for that root and confirm.
4. Reopen the HTTPS address in the browser. Connect the VPN first if away from home.

If the full-trust toggle is missing, confirm the root profile actually installed and that device management does not prohibit it. [Apple's manual-trust instructions](https://support.apple.com/en-ca/102390).

### macOS (Safari, Chrome, Edge)

Open **Keychain Access**, select the **System** keychain, and import `root.crt` (dragging it into the keychain is supported). Open the imported certificate, expand **Trust**, and set SSL trust appropriately for your root, or **When using this certificate → Always Trust**. Close the dialog and authorize the change. Restart the browser if necessary. Firefox/Zen may need their separate import below.

Apple: [import certificates](https://support.apple.com/guide/keychain-access/add-certificates-to-a-keychain-kyca2431/mac) and [change trust settings](https://support.apple.com/guide/keychain-access/change-the-trust-settings-of-a-certificate-kyca11871/mac).

### Windows (Edge, Chrome)

Open `root.crt` and choose **Install Certificate**. For your own user, select **Current User**, then choose to place it in **Trusted Root Certification Authorities**. Verify the certificate before accepting the warning. For all users, an administrator can instead import it through MMC's **Certificates (Local Computer)** snap-in into that store. Restart the browser. Firefox/Zen may require separate trust configuration.

Microsoft: [Trusted Root Certification Authorities store](https://learn.microsoft.com/en-us/windows-hardware/drivers/install/trusted-root-certification-authorities-certificate-store).

### Linux system trust

For Debian/Ubuntu, copy the verified PEM-formatted `.crt` into the local CA directory and rebuild trust:

```bash
sudo cp /path/to/root.crt /usr/local/share/ca-certificates/mystical-mark-local.crt
sudo update-ca-certificates
```

For Fedora/RHEL and Arch/Manjaro systems using the shared p11-kit trust store:

```bash
sudo trust anchor /path/to/root.crt
sudo update-ca-trust
```

Your distro's trust tooling must be installed. Restart browsers. Sandboxed/Flatpak apps and browsers with independent stores may not pick up system trust; use their own certificate controls where supported. Do not change TLS verification settings globally.

References: [Ubuntu custom trust store](https://documentation.ubuntu.com/server/how-to/security/install-a-root-ca-certificate-in-the-trust-store/) and [Arch TLS trust management](https://wiki.archlinux.org/title/Transport_Layer_Security).

### Firefox and Zen (desktop)

Open Settings, search for **certificates**, then **View Certificates → Authorities → Import**. Choose `root.crt` and enable the website-identification trust option. Confirm, then reload the private HTTPS address. Zen is Firefox-based; exact labels may vary. Some installations already honor OS roots, so check for the CA before importing a duplicate.

Reference: [Mozilla CA configuration](https://support.mozilla.org/en-US/kb/setting-certificate-authorities-firefox).

### Android phones and tablets

Transfer `root.crt` onto the device. In Settings, search for **Install a certificate**. Common paths are **Security & privacy → More security settings → Encryption & credentials** or manufacturer-specific equivalents. Choose **CA certificate** (not a Wi-Fi/client certificate), authenticate with the device PIN, review the warning, and select the file.

Use a browser that trusts user-installed CAs, and reopen the HTTPS URL. Work profiles, managed devices and individual apps can have separate trust rules; successful installation does not force every app to trust user roots. If the browser still rejects it, use that browser's documented CA support or another supported browser; do not bypass the warning.

Google: [certificate management](https://support.google.com/pixelphone/answer/2844832?hl=en), [Android trust configuration](https://developer.android.com/privacy-and-security/security-config).

### ChromeOS / Chromebook

In Chrome settings, search **Manage certificates**, open **Authorities**, and import `root.crt` with website-identification trust. On managed Chromebooks, ask the administrator to deploy the CA using Chrome/Google device policy. Names and certificate-manager placement vary by release.

Reference: [Google managed-device certificates](https://knowledge.workspace.google.com/admin/devices/add-and-assign-digital-certificates-for-managed-devices).

## Troubleshooting

| Symptom | Check |
|---|---|
| Connection refused | Both processes are running; host is awake; IP/port correct; firewall allows only your intended sources |
| 403 “Private LAN / VPN access only” | Caddy sees a source outside the allowlist; inspect VPN routing and actual client source subnet |
| Rejected Host header | Rerun LAN configuration with the intended address, then restart Studio |
| Unknown certificate authority | Wrong root, missing full trust, separate browser trust store, or Caddy running under another account |
| Certificate name mismatch | Browser URL differs from the IP/hostname configured in Caddy |
| Login does not stick | Use the configured HTTPS URL after enabling LAN mode; HTTP cannot carry the Secure session cookie |

To remove trust, delete only this CA/profile from the relevant authority store (on iOS, remove the installed profile; on Android, remove its user credential). Do not clear all certificates. Delete the host's CA storage only when you intend to recreate it and reinstall trust on every client.
