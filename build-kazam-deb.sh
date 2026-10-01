#!/bin/bash
set -e

BASE="$(cd "$(dirname "$0")" && pwd)"
SRC="$BASE/kazam"
PKG="$BASE/package"
DIST="$BASE/dist"

VERSION="2.0.0"
DEB_NAME="kazam_${VERSION}_all.deb"

echo "=== Xóa package cũ ==="
rm -rf "$PKG"

echo "=== Tạo cấu trúc package ==="
mkdir -p "$PKG/DEBIAN"
mkdir -p "$PKG/opt/kazam"
mkdir -p "$PKG/usr/bin"
mkdir -p "$PKG/usr/share/applications"
mkdir -p "$PKG/usr/share/icons/hicolor/64x64/apps"

echo "=== Copy source Kazam ==="
cp -r "$SRC/kazam" "$PKG/opt/kazam/"
cp -r "$SRC/data" "$PKG/opt/kazam/"
cp -r "$SRC/img" "$PKG/opt/kazam/"
cp -r "$SRC/share" "$PKG/opt/kazam/" 2>/dev/null || true
mkdir -p "$PKG/opt/kazam/bin"
cp "$SRC/bin/kazam" "$PKG/opt/kazam/bin/kazam"
chmod 755 "$PKG/opt/kazam/bin/kazam"
find "$PKG/opt/kazam" -type d -name "__pycache__" -prune -exec rm -rf {} +
find "$PKG/opt/kazam" -type f -name "*.pyc" -delete
cp "$SRC/kazam.png" \
   "$PKG/usr/share/icons/hicolor/64x64/apps/kazam.png"

echo "=== Tạo launcher ==="
cat > "$PKG/usr/bin/kazam" <<'EOF'
#!/bin/sh
export PYTHONPATH=/opt/kazam
cd /opt/kazam
exec /usr/bin/python3 /opt/kazam/bin/kazam "$@"
EOF

chmod 755 "$PKG/usr/bin/kazam"

echo "=== Tạo desktop entry ==="
cat > "$PKG/usr/share/applications/kazam.desktop" <<'EOF'
[Desktop Entry]
Name=Kazam
Comment=Screen recording and screenshot
Exec=/usr/bin/kazam
Icon=kazam
Terminal=false
Type=Application
Categories=AudioVideo;Graphics;
StartupNotify=true
EOF

chmod 644 "$PKG/usr/share/applications/kazam.desktop"

echo "=== Tạo control ==="
cat > "$PKG/DEBIAN/control" <<EOF
Package: kazam
Version: $VERSION
Section: video
Priority: optional
Architecture: all
Maintainer: Kazam Ubuntu Package
Depends: python3, python3-gi, python3-cairo, python3-dbus, python3-xlib, python3-xdg, python3-gst-1.0, python3-distro, gir1.2-gtk-3.0, gir1.2-gstreamer-1.0, gstreamer1.0-tools, gstreamer1.0-pipewire
Description: Screen recording and screenshot application
 Kazam is a screen recording and screenshot application for Linux.
EOF

echo "=== Build DEB ==="
mkdir -p "$DIST"
rm -f "$DIST/$DEB_NAME"

fakeroot dpkg-deb --build "$PKG" "$DIST/$DEB_NAME"

echo
echo "======================================"
echo " BUILD THÀNH CÔNG"
echo "======================================"
echo
echo "File:"
echo "$DIST/$DEB_NAME"
echo
ls -lh "$DIST/$DEB_NAME"
