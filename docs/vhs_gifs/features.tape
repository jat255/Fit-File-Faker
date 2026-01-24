# VHS Features Demo - Fit File Faker
#
# This demo showcases the CLI features of fit-file-faker
# without complex interactive navigation.
#
# To generate the GIF, run: vhs features.tape
# Output:
#   Output <path>.gif               Create a GIF output at the given <path>
#   Output <path>.mp4               Create an MP4 output at the given <path>
#   Output <path>.webm              Create a WebM output at the given <path>
#
# Require:
#   Require <string>                Ensure a program is on the $PATH to proceed
#
# Settings:
#   Set FontSize <number>           Set the font size of the terminal
#   Set FontFamily <string>         Set the font family of the terminal
#   Set Height <number>             Set the height of the terminal
#   Set Width <number>              Set the width of the terminal
#   Set LetterSpacing <float>       Set the font letter spacing (tracking)
#   Set LineHeight <float>          Set the font line height
#   Set LoopOffset <float>%         Set the starting frame offset for the GIF loop
#   Set Theme <json|string>         Set the theme of the terminal
#   Set Padding <number>            Set the padding of the terminal
#   Set Framerate <number>          Set the framerate of the recording
#   Set PlaybackSpeed <float>       Set the playback speed of the recording
#   Set MarginFill <file|#000000>   Set the file or color the margin will be filled with.
#   Set Margin <number>             Set the size of the margin. Has no effect if MarginFill isn't set.
#   Set BorderRadius <number>       Set terminal border radius, in pixels.
#   Set WindowBar <string>          Set window bar type. (one of: Rings, RingsRight, Colorful, ColorfulRight)
#   Set WindowBarSize <number>      Set window bar size, in pixels. Default is 40.
#   Set TypingSpeed <time>          Set the typing speed of the terminal. Default is 50ms.
#
# Sleep:
#   Sleep <time>                    Sleep for a set amount of <time> in seconds
#
# Type:
#   Type[@<time>] "<characters>"    Type <characters> into the terminal with a
#                                   <time> delay between each character
#
# Keys:
#   Escape[@<time>] [number]        Press the Escape key
#   Backspace[@<time>] [number]     Press the Backspace key
#   Delete[@<time>] [number]        Press the Delete key
#   Insert[@<time>] [number]        Press the Insert key
#   Down[@<time>] [number]          Press the Down key
#   Enter[@<time>] [number]         Press the Enter key
#   Space[@<time>] [number]         Press the Space key
#   Tab[@<time>] [number]           Press the Tab key
#   Left[@<time>] [number]          Press the Left Arrow key
#   Right[@<time>] [number]         Press the Right Arrow key
#   Up[@<time>] [number]            Press the Up Arrow key
#   Down[@<time>] [number]          Press the Down Arrow key
#   PageUp[@<time>] [number]        Press the Page Up key
#   PageDown[@<time>] [number]      Press the Page Down key
#   Ctrl+<key>                      Press the Control key + <key> (e.g. Ctrl+C)
#
# Display:
#   Hide                            Hide the subsequent commands from the output
#   Show                            Show the subsequent commands in the output

Output features.gif

Require uv

Set Shell "bash"
Set FontSize 15
Set Width 1200
Set Height 600
Set Theme "Dracula"
Set TypingSpeed 30ms
Set PlaybackSpeed 1.0
Set WindowBar "Colorful"

# Title
Hide
Type "clear" Enter
Ctrl+V Ctrl+J
Ctrl+V Ctrl+J
Type "# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯"
Ctrl+V Ctrl+J
Type "# Fit File Faker - Feature Walkthrough"
Ctrl+V Ctrl+J
Type "# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯"
Ctrl+V Ctrl+J
Ctrl+V Ctrl+J
Enter
Show
Sleep 1.5s


# Feature 1: Help
Ctrl+V Ctrl+J
Type "#    → Feature 1: Display help and available commands" Enter Enter
Sleep 800ms
Type "uv run fit-file-faker --help" Sleep 300ms Enter
Sleep 4s

# Clear for next feature
Hide
Type "clear" Enter
Ctrl+V Ctrl+J
Ctrl+V Ctrl+J
Type "# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯"
Ctrl+V Ctrl+J
Type "# Fit File Faker - Feature Walkthrough"
Ctrl+V Ctrl+J
Type "# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯"
Ctrl+V Ctrl+J
Ctrl+V Ctrl+J
Enter
Show
Sleep 0.5s


# Feature 2: config paths
Ctrl+V Ctrl+J
Type "#    → Feature 2: Show configuration and cache directories" Enter Enter
Sleep 800ms
Type "uv run fit-file-faker --show-dirs" Sleep 300ms Enter
Sleep 4s

# Clear for next feature
Hide
Type "clear" Enter
Ctrl+V Ctrl+J
Ctrl+V Ctrl+J
Type "# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯"
Ctrl+V Ctrl+J
Type "# Fit File Faker - Feature Walkthrough"
Ctrl+V Ctrl+J
Type "# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯"
Ctrl+V Ctrl+J
Ctrl+V Ctrl+J
Enter
Show
Sleep 0.5s


# Feature 3: list configured profiles
Ctrl+V Ctrl+J
Type "#    → Feature 3: List configured profiles" Enter Enter
Sleep 800ms
Type "uv run fit-file-faker --list-profiles" Sleep 300ms Enter
Sleep 4s

# Clear for next feature
Hide
Type "clear" Enter
Ctrl+V Ctrl+J
Ctrl+V Ctrl+J
Type "# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯"
Ctrl+V Ctrl+J
Type "# Fit File Faker - Feature Walkthrough"
Ctrl+V Ctrl+J
Type "# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯"
Ctrl+V Ctrl+J
Ctrl+V Ctrl+J
Enter
Show
Sleep 0.5s


# Feature summary
Set TypingSpeed 20ms
Ctrl+V Ctrl+J
Type "#    → Features: What does fit-file-faker do?"
Ctrl+V Ctrl+J
Type "#       • Modifies FIT files to appear as Garmin devices" Ctrl+V Ctrl+J
Type "#       • Enables Training Effect on Garmin Connect" Ctrl+V Ctrl+J
Type "#       • Supports TrainingPeaks Virtual, Zwift, MyWhoosh, etc." Ctrl+V Ctrl+J
Type "#       • Multiple profiles for different apps/accounts" Ctrl+V Ctrl+J
Type "#       • Configurable device simulation (Edge, Tacx, etc.)" Ctrl+V Ctrl+J
Sleep 2s
Set TypingSpeed 50ms

# Clear for next feature
Hide
Type "clear" Enter
Ctrl+V Ctrl+J
Ctrl+V Ctrl+J
Type "# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯"
Ctrl+V Ctrl+J
Type "# Fit File Faker - Feature Walkthrough"
Ctrl+V Ctrl+J
Type "# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯"
Ctrl+V Ctrl+J
Ctrl+V Ctrl+J
Enter
Show
Sleep 0.5s

# # Feature 6: Example commands
Set TypingSpeed 20ms
Ctrl+V Ctrl+J
Type "#    → Common commands:"
Ctrl+V Ctrl+J Ctrl+V Ctrl+J

Type "#       • Edit a single file:" Ctrl+V Ctrl+J
Type "#          > fit-file-faker /path/to/activity.fit" Sleep 0.5s Ctrl+V Ctrl+J Ctrl+V Ctrl+J

Type "#       • Edit and upload to Garmin Connect:" Ctrl+V Ctrl+J
Type "#          > fit-file-faker -u /path/to/activity.fit" Sleep 0.5s Ctrl+V Ctrl+J Ctrl+V Ctrl+J

Type "#       • Upload all new files from configured directory:" Ctrl+V Ctrl+J
Type "#          > fit-file-faker -ua" Sleep 0.5s Ctrl+V Ctrl+J Ctrl+V Ctrl+J

Type "#       • Monitor directory for new/edited workout files:" Ctrl+V Ctrl+J
Type "#          > fit-file-faker -m" Sleep 0.5s Ctrl+V Ctrl+J Ctrl+V Ctrl+J

Type "#       • Use specific profile:" Ctrl+V Ctrl+J
Type "#          > fit-file-faker --profile zwift -m" Sleep 0.5s Ctrl+V Ctrl+J Ctrl+V Ctrl+J

Type "#       • Edit profiles:" Ctrl+V Ctrl+J
Type "#          > fit-file-faker --config-menu" Sleep 0.5s Ctrl+V Ctrl+J
Sleep 2s
Set TypingSpeed 50ms

# Clear for next feature
Hide
Type "clear" Enter
Ctrl+V Ctrl+J
Ctrl+V Ctrl+J
Type "# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯"
Ctrl+V Ctrl+J
Type "# Fit File Faker - Feature Walkthrough"
Ctrl+V Ctrl+J
Type "# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯"
Ctrl+V Ctrl+J
Ctrl+V Ctrl+J
Enter
Show
Sleep 0.5s

Set TypingSpeed 20ms
Ctrl+V Ctrl+J
Type "#    → Learn more:"
Ctrl+V Ctrl+J
Type "#       • https://github.com/jat255/Fit-File-Faker" Ctrl+V Ctrl+J
Type "#       • https://jat255.github.io/Fit-File-Faker/" Ctrl+V Ctrl+J
Sleep 4s
