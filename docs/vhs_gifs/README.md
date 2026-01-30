# VHS Video Creation Guide

This directory contains VHS tape files for generating terminal demo videos of Fit File Faker's features.

## What is VHS?

[VHS](https://github.com/charmbracelet/vhs) is a tool for generating terminal videos and GIFs from plain text instructions. It's part of the Charm ecosystem and allows you to create reproducible, high-quality terminal recordings.

**Note**: This project uses MP4 format instead of GIF for better quality, smaller file sizes, and native video controls in the documentation.

## Installation

### macOS (Homebrew)

```bash
brew install vhs
```

### Linux

```bash
# Install from releases
go install github.com/charmbracelet/vhs@latest

# Or use your package manager (if available)
```

### Windows

```bash
# Install via Scoop
scoop install vhs

# Or install via Go
go install github.com/charmbracelet/vhs@latest
```

For more installation options, see the [VHS documentation](https://github.com/charmbracelet/vhs#installation).

## Requirements

VHS requires:
- `ffmpeg` for video/GIF generation
- `ttyd` for the terminal server (installed automatically by VHS)
- A shell (bash, zsh, etc.)

Install ffmpeg if not already present:

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
scoop install ffmpeg
```

## Project Setup

Before recording VHS tapes, ensure you have Fit File Faker installed:

```bash
# From the project root
uv sync
```

## Creating Videos

### Generating an MP4 from a tape file

```bash
# Generate a specific video
vhs features.tape

# This will create features.mp4 in the current directory
```

### Regenerating all videos

```bash
# From the docs/vhs_gifs directory
vhs config_new.tape
vhs config_edit.tape
vhs features.tape
```

## Tape File Structure

Each `.tape` file contains VHS commands that control the terminal recording. Here's an overview of the key sections:

### 1. Output Configuration

```
Output features.mp4
```

Specifies the output filename. Can be `.gif`, `.mp4`, or `.webm`. **This project uses `.mp4` format** for optimal quality and file size.

### 2. Requirements

```
Require uv
```

Ensures the required program is available on `$PATH` before proceeding.

### 3. Terminal Settings

```
Set Shell "bash"
Set FontSize 15
Set Width 1200
Set Height 600
Set Theme "Dracula"
Set TypingSpeed 30ms
Set PlaybackSpeed 1.0
Set WindowBar "Colorful"
```

Configure the terminal appearance and behavior:
- `Shell`: Shell to use (bash, zsh, etc.)
- `FontSize`: Terminal font size
- `Width/Height`: Terminal dimensions in pixels
- `Theme`: Color theme (Dracula, Monokai, etc.)
- `TypingSpeed`: How fast text appears (simulates typing)
- `PlaybackSpeed`: Playback speed multiplier
- `WindowBar`: Window decoration style

### 4. Commands

```
Type "uv run fit-file-faker --help" Enter
Sleep 2s
```

Available commands:
- `Type`: Simulate typing text
- `Enter`: Press Enter key
- `Sleep`: Pause for specified duration
- `Ctrl+<key>`: Send control sequences
- `Hide`/`Show`: Hide/show commands in output
- `Up`/`Down`/`Left`/`Right`: Arrow keys
- `Tab`, `Space`, `Backspace`, etc.

### 5. Visibility Control

```
Hide
Type "clear" Enter
# ... setup commands ...
Show
```

Commands between `Hide` and `Show` execute but don't appear in the recording. Useful for setup/cleanup.

## Creating New Tape Files

To create a new demo:

1. **Create a new `.tape` file**:

```bash
touch my_demo.tape
```

2. **Start with the template**:

```
Output my_demo.mp4

Require uv

Set Shell "bash"
Set FontSize 15
Set Width 1200
Set Height 600
Set Theme "Dracula"
Set TypingSpeed 30ms
Set PlaybackSpeed 1.0
Set WindowBar "Colorful"

# Your commands here
Type "uv run fit-file-faker --help" Enter
Sleep 2s
```

3. **Test the recording**:

```bash
vhs my_demo.tape
```

4. **Iterate**: Adjust timing, commands, and appearance until satisfied.

## Tips for Good Recordings

1. **Keep it focused**: Each video should demonstrate one feature or workflow
2. **Use appropriate delays**: 
   - `Sleep 0.5s` - Quick pause between related commands
   - `Sleep 2s` - Let users read output
   - `Sleep 4s` - Complex output that needs review
3. **Clear between sections**: Use `Hide`/`Show` to reset the terminal without clutter
4. **Reasonable dimensions**: 1200x600 works well for most demos
5. **Consistent styling**: Use the same theme/font across all videos
6. **Add context**: Use comments (`#`) to explain what's happening
7. **Test on different platforms**: VHS behavior may vary slightly
8. **Use MP4 format**: Provides better compression than GIF while maintaining quality

## Current Demos

### features.tape
Comprehensive walkthrough of CLI features:
- Help command (`--help`)
- Directory information (`--show-dirs`)
- Profile listing (`--list-profiles`)
- Feature summary
- Common command examples
- Project links

**Output**: `features.mp4`

### config_new.tape
Interactive demo of creating a new profile through the config menu.

**Output**: `config_new.mp4`

### config_edit.tape
Interactive demo of editing an existing profile.

**Output**: `config_edit.mp4`

## Troubleshooting

### Video file is too large

Reduce file size by:
- Decreasing terminal dimensions (`Set Width/Height`)
- Reducing `Framerate` (default: 60)
- Shortening `Sleep` durations
- MP4 format is already optimized; avoid using `.gif` or `.webm`

### Commands execute too fast

Increase `TypingSpeed` and add more `Sleep` commands:

```
Set TypingSpeed 50ms
Type "command" Enter
Sleep 3s  # Give users time to read
```

### Terminal looks wrong

Adjust theme or colors:

```
Set Theme "Dracula"  # Try different themes
Set FontFamily "JetBrains Mono"
```

### Recording fails

Check requirements:
```bash
which ffmpeg  # Should return a path
which ttyd    # Should return a path
```

## Advanced Features

### Custom Fonts

```
Set FontFamily "JetBrains Mono"
Set LetterSpacing 1.0
Set LineHeight 1.4
```

### Window Styling

```
Set Padding 20
Set BorderRadius 10
Set Margin 20
Set MarginFill "#000000"
Set WindowBarSize 40
```

### Loop Control

```
Set LoopOffset 10%  # Start loop 10% into the GIF
```

## Resources

- [VHS GitHub Repository](https://github.com/charmbracelet/vhs)
- [VHS Documentation](https://github.com/charmbracelet/vhs#vhs)
- [Charm Blog - Announcing VHS](https://charm.sh/blog/vhs-intro/)
- [Example VHS Tapes](https://github.com/charmbracelet/vhs/tree/main/examples)

## Integration with Documentation

These videos are embedded in the project documentation using HTML5 video tags:
- Main README (`README.md`)
- Documentation site (`docs/index.md`)

Videos are embedded using:
```html
<video width="800" autoplay loop muted playsinline>
  <source src="vhs_gifs/features.mp4" type="video/mp4">
  Your browser does not support the video tag.
</video>
```

The `autoplay loop muted playsinline` attributes make the video behave like a GIF (auto-playing and looping) while providing better quality and controls.

When updating videos, regenerate them and commit both the `.tape` files and `.mp4` outputs to the repository.
