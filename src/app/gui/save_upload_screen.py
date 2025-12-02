"""
Save/Upload Screen - Final configuration & upload (Step 3)
"""

import os
import threading
import subprocess
import sys
import flet as ft
from configs.config import Config
from app.services import VideoMerger
# TODO: import date library thingy para sa placeholder filename

class SaveUploadScreen:
    """Third screen: Configure output and upload settings"""
    
    def __init__(self, videos=None, page=None, on_save=None, on_upload=None, on_back=None):
        self.page = page
        self.videos = videos or []  # List of arranged videos from Step 2
        self.on_save = on_save  # Callback for "Save" button
        self.on_upload = on_upload  # Callback for "Save / Upload" button
        self.on_back = on_back  # Callback for "Back" button
        self.main_window = None # para mareference ni main_window sarili in this class
        self.file_list = ft.Column(spacing=5)
        self.selected_video_index = 0  # Track which video to preview
        self.merger = VideoMerger()  # Initialize video merger
        self.is_merging = False  # Track merge status
        self.progress_bar = None  # Reference to progress bar for updates
        self.progress_text = None  # Reference to progress text for updates
        self.progress_container = None  # Reference to progress container
        self.save_location = os.path.expanduser("~/Videos")  # Default save location
        
        # TODO: Initialize form fields
        # TODO: Load default values from Config

    def set_videos(self, videos):
        self.videos = videos or []
        self.selected_video_index = 0
        
    def _select_video(self, index):
        """Select a video for preview"""
        if 0 <= index < len(self.videos):
            self.selected_video_index = index
            if self.main_window:
                self.main_window.go_to_step(2)
    
    def _on_merge_progress(self, message: str, percentage: float):
        """Handle merge progress updates"""
        print(f"Merge Progress: {message} ({percentage}%)")
        if self.progress_bar and self.progress_text and self.page:
            self.progress_bar.value = percentage / 100.0
            self.progress_text.value = f"{message} ({int(percentage)}%)"
            self.page.update()
    
    def _on_merge_error(self, error_message: str):
        """Handle merge errors"""
        print(f"Merge Error: {error_message}")
        if self.progress_container and self.page:
            self.progress_container.visible = False
            self.page.update()
        if self.page:
            snackbar_error = ft.SnackBar(
                content=ft.Text(f"Merge failed: {error_message}", color=ft.Colors.WHITE),
                bgcolor=ft.Colors.with_opacity(0.9, "#f03a1a"),
            )
            self.page.overlay.append(snackbar_error)
            snackbar_error.open = True
            self.page.update()
        self.is_merging = False
    
    def _on_merge_complete(self, output_path: str):
        """Handle merge completion"""
        print(f"Merge complete! Output: {output_path}")
        if self.progress_container and self.page:
            self.progress_container.visible = False
            self.page.update()

        # Create confirmation dialog so the user won't miss completion
        def open_folder(e):
            try:
                folder = os.path.dirname(output_path)
                if os.name == 'nt':
                    os.startfile(folder)
                elif sys.platform == 'darwin':
                    subprocess.run(["open", folder])
                else:
                    subprocess.run(["xdg-open", folder])
            except Exception as ex:
                print(f"Failed to open folder: {ex}")
            finally:
                dlg.open = False
                if self.page:
                    self.page.update()

        def close_dialog(e):
            dlg.open = False
            if self.page:
                self.page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Merge Complete"),
            content=ft.Column([
                ft.Text("The merged video was created:"),
                ft.Text(output_path, size=12),
            ]),
            actions=[
                ft.TextButton("Open Folder", on_click=open_folder),
                ft.TextButton("OK", on_click=close_dialog),
            ],
        )
        if self.page:
            self.page.overlay.append(dlg)
            dlg.open = True
            self.page.update()

        self.is_merging = False
        
    def build(self):
        """Build and return save/upload screen layout (Frame 4)"""

        # Save Settings section
        filename_field = ft.TextField(label="Filename", value=f"{Config.DEFAULT_OUTPUT_FORMAT}")
        format_dropdown = ft.Dropdown(
            label="File Type",
            options=[ft.dropdown.Option(fmt) for fmt in Config.SUPPORTED_VIDEO_FORMATS],
            value=Config.DEFAULT_VIDEO_FORMAT,
            width=150,
            menu_height=200,
            color=ft.Colors.WHITE,
            bgcolor=ft.Colors.GREY_900,
            text_style=ft.TextStyle(color=ft.Colors.WHITE),
        )
        codec_dropdown = ft.Dropdown(
            label="Codec",
            options=[ft.dropdown.Option(codec) for codec in Config.SUPPORTED_CODECS],
            value=Config.DEFAULT_CODEC,
            width=150,
            menu_height=200,
            color=ft.Colors.WHITE,
            bgcolor=ft.Colors.GREY_900,
            text_style=ft.TextStyle(color=ft.Colors.WHITE),
        )
        
        # File picker callback and save section (choose location button shown in right column)
        def on_directory_result(e):
            """Handle directory selection result"""
            if e.path:
                self.save_location = e.path
                save_location_display.value = f"Save to: {self.save_location}"
                if self.page:
                    self.page.update()

        # File picker for directory selection (appended later)
        file_picker = ft.FilePicker(on_result=on_directory_result)

        # Save location display (defined early so UI sections can reference it)
        save_location_display = ft.Text(
            f"Save to: {self.save_location}",
            size=12,
            color=ft.Colors.WHITE70,
        )

        save_settings_section = ft.Column([
            ft.Text("Save Settings", size=14, weight=ft.FontWeight.BOLD),
            filename_field,
            format_dropdown,
            codec_dropdown,
            save_location_display,
            ft.Divider(),
        ])

        # Upload Settings section
        title_field = ft.TextField(label="Title")
        tags_field = ft.TextField(label="Tags (comma separated)")
        visibility_dropdown = ft.Dropdown(
            label="Visibility",
            options=[
                ft.dropdown.Option("Public"),
                ft.dropdown.Option("Unlisted"),
                ft.dropdown.Option("Private"),
            ],
            value="Public",
            width=150,
            color=ft.Colors.WHITE,
            bgcolor=ft.Colors.GREY_900,
            text_style=ft.TextStyle(color=ft.Colors.WHITE),
        )
        description_field = ft.TextField(label="Description", multiline=True, min_lines=3, max_lines=5)
        upload_settings_section = ft.Column([
            ft.ElevatedButton("Edit Upload Settings", on_click=lambda e: open_upload_settings_dialog(e)),
            ft.Divider(),
        ])

        # Progress bar and text
        self.progress_bar = ft.ProgressBar(width=300, value=0, color="#00897B")
        self.progress_text = ft.Text("Starting merge...", size=12, color=ft.Colors.WHITE70)
        self.progress_container = ft.Container(
            content=ft.Column([
                ft.Text("Merging Videos", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                self.progress_bar,
                self.progress_text,
            ], spacing=10),
            padding=15,
            bgcolor=ft.Colors.with_opacity(0.1, "#00897B"),
            border_radius=8,
            visible=False,  # Hidden initially
        )

        def on_choose_location(e):
            """Trigger platform file picker to choose directory"""
            if self.page:
                file_picker.get_directory_path()

        # append the file picker to the page overlay so it can be invoked
        if self.page:
            self.page.overlay.append(file_picker)

        # Button click handlers
        def on_save_click(e):
            """Handle Save button click"""
            if self.is_merging:
                if self.page:
                    snackbar_busy = ft.SnackBar(
                        content=ft.Text("Merge in progress...", color=ft.Colors.WHITE),
                        bgcolor=ft.Colors.with_opacity(0.9, "#FF9800"),
                    )
                    self.page.overlay.append(snackbar_busy)
                    snackbar_busy.open = True
                    self.page.update()
                return
            
            # Validate inputs
            if not filename_field.value or not self.videos:
                if self.page:
                    snackbar_error = ft.SnackBar(
                        content=ft.Text("Please enter filename and select videos", color=ft.Colors.WHITE),
                        bgcolor=ft.Colors.with_opacity(0.9, "#f03a1a"),
                    )
                    self.page.overlay.append(snackbar_error)
                    snackbar_error.open = True
                    self.page.update()
                return
            
            # Start merging
            self.is_merging = True
            output_filename = f"{filename_field.value}{format_dropdown.value}"
            output_path = os.path.join(self.save_location, output_filename)
            
            # Show progress container
            if self.progress_container and self.page:
                self.progress_container.visible = True
                self.progress_bar.value = 0
                self.progress_text.value = "Starting merge..."
                self.page.update()
            
            # Set callbacks
            self.merger.set_progress_callback(self._on_merge_progress)
            self.merger.set_error_callback(self._on_merge_error)
            self.merger.set_complete_callback(self._on_merge_complete)
            
            # Start merge in a background thread so UI remains responsive
            t = threading.Thread(
                target=self.merger.merge_videos,
                args=(self.videos, output_path),
                kwargs={"codec": codec_dropdown.value or "H.264"},
                daemon=True,
            )
            t.start()

        # Buttons section
        buttons_section = ft.Column([
            ft.ElevatedButton("Save", icon=ft.Icons.SAVE, on_click=on_save_click),
            ft.ElevatedButton("Upload", icon=ft.Icons.UPLOAD),
            # Placeholder for status tags
        ])

        # Dialog logic
        def close_upload_settings_dialog(e):
            upload_settings_dialog.open = False
            self.page.update()

        def open_upload_settings_dialog(e):
            upload_settings_dialog.open = True
            self.page.update()

        upload_settings_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Upload Settings"),
            content=ft.Column([
                title_field,
                tags_field,
                visibility_dropdown,
                description_field,
            ], spacing=10),
            actions=[
                ft.TextButton("Save", on_click=close_upload_settings_dialog),
                ft.TextButton("Cancel", on_click=close_upload_settings_dialog),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            content_padding=ft.padding.only(left=200, right=200),
            on_dismiss=lambda e: print("Upload settings dialog dismissed!"),
        )

        # Add dialog to page overlay
        if self.page:
            self.page.overlay.append(upload_settings_dialog)

        # Build video list (no arrange/remove buttons)
        video_list_controls = []
        if not self.videos:
            video_list_controls.append(
                ft.Text("No videos selected.", color=ft.Colors.WHITE70)
            )
        else:
            for i, video_path in enumerate(self.videos):
                video_name = video_path.split('/')[-1] if '/' in video_path else video_path.split('\\')[-1]
                video_item = ft.Container(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Text(str(i + 1), color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                            width=30, height=30, bgcolor=ft.Colors.with_opacity(0.8, "#00ACC1"),
                            border_radius=15, alignment=ft.alignment.center,
                        ),
                        ft.Text(video_name, color=ft.Colors.WHITE, expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ], spacing=10),
                    padding=10,
                    bgcolor=ft.Colors.with_opacity(0.05, "#FFFFFF") if i == self.selected_video_index else ft.Colors.with_opacity(0.02, "#FFFFFF"),
                    border_radius=8,
                    on_click=lambda _, idx=i: self._select_video(idx),
                )
                video_list_controls.append(video_item)

        # Calculate dynamic height for video list container
        num_videos = len(self.videos)
        video_list_height = min(max(num_videos * 40, 80), 160)  # 40px per video, min 80, max 160 (fits 4 videos)

        # --- LOGIC FOR PREVIEW PLAYER ---
        preview_content = None
        
        # Check if we have videos and a valid index
        if self.videos and 0 <= self.selected_video_index < len(self.videos):
            current_video_path = self.videos[self.selected_video_index]
            
            # Create the Flet Video Player
            preview_content = ft.Video(
                playlist=[ft.VideoMedia(current_video_path)],
                playlist_mode=ft.PlaylistMode.SINGLE,
                fill_color=ft.Colors.BLACK,
                aspect_ratio=16/9,
                volume=100,
                autoplay=True,
                filter_quality=ft.FilterQuality.HIGH,
                muted=False,
            )
        else:
            # Fallback if no video is selected
            preview_content = ft.Column([
                ft.Icon(ft.Icons.VIDEO_FILE_OUTLINED, size=64, color=ft.Colors.with_opacity(0.6, "#00ACC1")),
                ft.Text(
                    "No video selected",
                    color=ft.Colors.WHITE70,
                    size=14,
                    text_align=ft.TextAlign.CENTER,
                ),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10, alignment=ft.MainAxisAlignment.CENTER)

        # Main layout
        return ft.Container(
            content=ft.Row(
                [
                    # Left column: Video list above, preview below
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text("Selected Videos", size=16, weight=ft.FontWeight.BOLD),
                                ft.Container(
                                    content=ft.Column(video_list_controls, scroll=ft.ScrollMode.AUTO),
                                    height=video_list_height,
                                    bgcolor=ft.Colors.with_opacity(0.03, "#FFFFFF"),
                                    border_radius=8,
                                    padding=8,
                                ),
                                ft.Container(height=10), # Spacer
                                ft.Text("Video Preview", size=16, weight=ft.FontWeight.BOLD),
                                ft.Container(
                                    content=preview_content,
                                    bgcolor=ft.Colors.BLACK,
                                    alignment=ft.alignment.center,
                                    height=200,
                                    border_radius=8,
                                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                                ),
                            ],
                            expand=True,
                            spacing=10,
                        ),
                        expand=1,
                        padding=10,
                    ),

                    # Right column: Settings (larger)
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text("Save", size=20, weight=ft.FontWeight.BOLD),
                                ft.Divider(),
                                save_settings_section,
                                ft.Row([
                                                            ft.ElevatedButton(
                                                                "Choose Location",
                                                                icon=ft.Icons.FOLDER_OPEN,
                                                                on_click=on_choose_location,
                                                                width=150,
                                                            ),
                                                        ]),
                                save_location_display,
                                self.progress_container,  # Progress bar here
                                ft.Text("Upload", size=20, weight=ft.FontWeight.BOLD),
                                ft.Divider(),
                                upload_settings_section,
                                buttons_section,
                            ],
                            scroll=ft.ScrollMode.AUTO,
                        ),
                        expand=2,
                        padding=20,
                        bgcolor=ft.Colors.with_opacity(0.1, "#1A1A1A"),
                    ),
                ],
                expand=True,
            ),
            padding=20,
            expand=True,
        )