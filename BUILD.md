# Building QuantumDownloader

## Option 1: GitHub Actions (recommended — no local setup needed)

1. Push this repo to GitHub:
```bash
cd /storage/emulated/0/New_Folder/PY_Projects/GUI_PROJECTS/Quantum-Downloader
git init
git add .
git commit -m "initial"
gh repo create quantum-downloader --public --push
```

2. Go to your repo on GitHub → **Actions** tab
3. Click **"Build QuantumDownloader"** → **"Run workflow"**
4. Wait ~15 min for all builds
5. Download artifacts: APK, EXE, Linux AppImage from the run page

## Option 2: Local build on this device (slow, requires ~3GB free)

```bash
# Install Java
sudo apt update
sudo apt install -y openjdk-17-jdk unzip wget

# Install Flutter SDK
cd ~
wget https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_3.29.2-stable.tar.xz
tar xf flutter_linux_3.29.2-stable.tar.xz
echo 'export PATH="$PATH:$HOME/flutter/bin"' >> ~/.bashrc
source ~/.bashrc
flutter precache --android
flutter config --android-sdk ~/Android/Sdk

# Install Android SDK command-line tools
mkdir -p ~/Android/Sdk/cmdline-tools
cd ~/Android/Sdk/cmdline-tools
wget https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
unzip commandlinetools-linux-11076708_latest.zip
mv cmdline-tools latest
echo 'export ANDROID_HOME=$HOME/Android/Sdk' >> ~/.bashrc
echo 'export PATH="$PATH:$ANDROID_HOME/cmdline-tools/latest/bin"' >> ~/.bashrc
source ~/.bashrc

# Accept licenses & install platform
yes | sdkmanager --licenses
sdkmanager "platform-tools" "platforms;android-34" "build-tools;34.0.0"

# Accept Android licenses for Flutter
flutter doctor --android-licenses
flutter doctor  # should show all checks green

# Build
cd /storage/emulated/0/New_Folder/PY_Projects/GUI_PROJECTS/Quantum-Downloader
pip install flet-cli==0.85.2 pyperclip
flet build apk --project quantum_downloader \
  --product "QuantumDownloader" \
  --org "com.quantumdownload" \
  --build-version "3.1.0" \
  --build-number 1 \
  "main(flet).py"

# APK will be in build/apk/
```
