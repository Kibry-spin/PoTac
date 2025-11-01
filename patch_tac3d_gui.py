#!/usr/bin/env python3
"""
Auto-patch script to integrate Tac3D sensor into GUI
Automatically modifies src/gui/main_window.py to add Tac3D support
"""

import sys
from pathlib import Path


def patch_main_window():
    """Patch main_window.py to add Tac3D support"""

    main_window_path = Path("src/gui/main_window.py")

    if not main_window_path.exists():
        print(f"❌ Error: {main_window_path} not found")
        return False

    # Read original file
    with open(main_window_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if already patched
    if 'tac3d_gui_extensions' in content:
        print("⚠️  File already patched with Tac3D support")
        return True

    print("Patching main_window.py...")

    original_content = content

    # Patch 1: Add import
    import_line = "from src.data.auto_recorder import DistanceBasedAutoRecorder, AutoRecordingState"
    new_import = """from src.data.auto_recorder import DistanceBasedAutoRecorder, AutoRecordingState
from src.gui.tac3d_gui_extensions import (
    create_tac3d_control_button,
    update_tac3d_status_in_control_panel,
    add_tac3d_to_recording
)"""

    if import_line in content:
        content = content.replace(import_line, new_import)
        print("✓ Added import statements")
    else:
        print("❌ Could not find import location")
        return False

    # Patch 2: Add status label in create_control_panel
    vt_status_pattern = "self.vt_sensor_status_label = Label(text='VT Sensors: None connected'"
    if vt_status_pattern in content:
        # Find the line and add after status_layout.add_widget(self.vt_sensor_status_label)
        lines = content.split('\n')
        new_lines = []
        added_label = False

        for i, line in enumerate(lines):
            new_lines.append(line)
            if vt_status_pattern in line:
                # Find the corresponding add_widget line
                j = i + 1
                while j < len(lines) and 'status_layout.add_widget(self.vt_sensor_status_label)' not in lines[j]:
                    j += 1
                    if j - i > 5:  # Safety limit
                        break

                if j < len(lines):
                    # Add lines after the add_widget
                    for k in range(i + 1, j + 1):
                        new_lines.append(lines[k])

                    # Add Tac3D status label
                    indent = ' ' * 8  # Match indentation
                    new_lines.append('')
                    new_lines.append(f'{indent}# Tac3D sensor status')
                    new_lines.append(f'{indent}self.tac3d_status_label = Label(')
                    new_lines.append(f"{indent}    text='Tac3D: None connected',")
                    new_lines.append(f'{indent}    font_size=\'12sp\',')
                    new_lines.append(f'{indent}    color=(1, 1, 0, 1)')
                    new_lines.append(f'{indent})')
                    new_lines.append(f'{indent}status_layout.add_widget(self.tac3d_status_label)')

                    # Skip to line j+1
                    for k in range(j + 1, len(lines)):
                        new_lines.append(lines[k])
                    added_label = True
                    break

        if added_label:
            content = '\n'.join(new_lines)
            print("✓ Added Tac3D status label")
        else:
            print("⚠️  Could not add Tac3D status label (manual edit required)")
    else:
        print("⚠️  VT status label not found (manual edit required)")

    # Patch 3: Add control button
    vt_config_button_pattern = "vt_config_button.bind(on_press=self.show_vt_sensor_config)"
    if vt_config_button_pattern in content:
        tac3d_button_code = """

        # Tac3D Sensor Config
        tac3d_config_button = create_tac3d_control_button(self)
        control_bar.add_widget(tac3d_config_button)"""

        content = content.replace(
            vt_config_button_pattern,
            vt_config_button_pattern + tac3d_button_code
        )
        print("✓ Added Tac3D config button")
    else:
        print("⚠️  VT config button not found (manual edit required)")

    # Patch 4: Add status update in update()
    update_vt_pattern = "self.update_vt_sensor_status()"
    if update_vt_pattern in content:
        tac3d_update_code = """

            # Update Tac3D sensor status
            update_tac3d_status_in_control_panel(self)"""

        content = content.replace(
            update_vt_pattern,
            update_vt_pattern + tac3d_update_code
        )
        print("✓ Added Tac3D status update")
    else:
        print("⚠️  update_vt_sensor_status() not found (manual edit required)")

    # Patch 5: Add to recording
    vt_recording_pattern = "vt_count += 1"
    total_sensors_pattern = "total_sensors = (1 if oak_added else 0) + vt_count"

    if vt_recording_pattern in content and total_sensors_pattern in content:
        # Add after vt_count section
        tac3d_recording_code = """

            # Add all Tac3D sensors
            tac3d_count = add_tac3d_to_recording(self, self.sync_recorder)"""

        # Find the position after vt_count code block
        lines = content.split('\n')
        new_lines = []
        added_recording = False

        for i, line in enumerate(lines):
            new_lines.append(line)

            if total_sensors_pattern in line and not added_recording:
                # Modify this line to include tac3d_count
                new_lines[-1] = line.replace(
                    "total_sensors = (1 if oak_added else 0) + vt_count",
                    "total_sensors = (1 if oak_added else 0) + vt_count + tac3d_count"
                )

                # Insert tac3d recording code before this line
                indent = ' ' * 12
                insert_lines = [
                    '',
                    f'{indent}# Add all Tac3D sensors',
                    f'{indent}tac3d_count = add_tac3d_to_recording(self, self.sync_recorder)',
                    ''
                ]

                # Insert before current line
                new_lines = new_lines[:-1] + insert_lines + [new_lines[-1]]
                added_recording = True

        if added_recording:
            content = '\n'.join(new_lines)
            print("✓ Added Tac3D to recording")
        else:
            print("⚠️  Could not add Tac3D to recording (manual edit required)")
    else:
        print("⚠️  Recording section not found (manual edit required)")

    # Write modified file
    try:
        # Backup original
        backup_path = main_window_path.with_suffix('.py.backup')
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_content)
        print(f"✓ Backup created: {backup_path}")

        # Write patched version
        with open(main_window_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ Patched {main_window_path}")

        return True

    except Exception as e:
        print(f"❌ Error writing file: {e}")
        return False


def main():
    print("="*60)
    print("Tac3D GUI Integration - Auto-Patch Script")
    print("="*60)
    print()

    if patch_main_window():
        print()
        print("="*60)
        print("✓ Patching completed successfully!")
        print("="*60)
        print()
        print("Next steps:")
        print("1. Review the changes in src/gui/main_window.py")
        print("2. Run the application: python main.py")
        print("3. Click 'Tac3D Config' button to connect sensors")
        print()
        print("If something went wrong:")
        print("- Restore from backup: src/gui/main_window.py.backup")
        print("- Follow manual instructions in TAC3D_GUI_INTEGRATION.md")
        return 0
    else:
        print()
        print("="*60)
        print("❌ Patching failed")
        print("="*60)
        print()
        print("Please follow manual integration steps in:")
        print("  TAC3D_GUI_INTEGRATION.md")
        return 1


if __name__ == "__main__":
    exit(main())
