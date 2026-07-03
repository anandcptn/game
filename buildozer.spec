[app]
title = Flappy Bird Clone
package.name = flappybirdclone
package.domain = org.example

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,wav,ogg
source.include_patterns = assets/*,assets/**/*

version = 1.0

requirements = python3,kivy

orientation = portrait
fullscreen = 1

icon.filename = assets/sprites/yellowbird-midflap.png

android.permissions = INTERNET
android.api = 34
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
