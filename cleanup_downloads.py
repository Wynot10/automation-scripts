"""
Cross-Platform Downloads Cleanup Script
========================================

Supported operating systems:
- Windows 10/11
- Linux

Purpose:
- Scans the current user's Downloads folder.
- Finds files older than FILE_AGE_DAYS based on last modification time.
- Supports DRY_RUN and LIVE modes.
- Windows: Moves files to the Recycle Bin.
- Linux: Moves files to the desktop Trash.
- Logs file names, modification times, and actions taken.
- Automatically rotates log files at 5 MB.
- Detects the operating system automatically.

Requirements:
- Python 3.10+
- Send2Trash

Install dependency:
    python -m pip install Send2Trash

Run:
    python downloads_cleanup.py
"""

import logging
import os
import platform
import sys

from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path

from send2trash import send2trash


# ============================================================================
# Configuration
# ============================================================================

# Number of days before a file qualifies for cleanup.
FILE_AGE_DAYS = 30

# SAFETY MODE
#
# True:
#   DRY RUN - files are NOT moved.
#
# False:
#   LIVE RUN - qualifying files are moved to the operating system's Trash.
DRY_RUN = True

# Maximum log file size: 5 MB.
MAX_LOG_SIZE = 5 * 1024 * 1024

# Number of rotated log files to retain.
BACKUP_LOG_COUNT = 5

# Log file name.
LOG_FILE_NAME = "downloads_cleanup.log"


# ============================================================================
# Platform Detection
# ============================================================================

OPERATING_SYSTEM = platform.system()

if OPERATING_SYSTEM == "Windows":
    TRASH_NAME = "Recycle Bin"

elif OPERATING_SYSTEM == "Linux":
    TRASH_NAME = "Trash"

else:
    print(
        f"[ERROR] Unsupported operating system: {OPERATING_SYSTEM}"
    )
    print("Supported operating systems: Windows and Linux.")
    raise SystemExit(1)


# ============================================================================
# Downloads Folder Detection
# ============================================================================

def get_downloads_folder() -> Path:
    """
    Determine the current user's Downloads directory.

    Windows:
        Uses ~/Downloads.

    Linux:
        Reads XDG_DOWNLOAD_DIR from ~/.config/user-dirs.dirs
        when available, falling back to ~/Downloads.
    """

    home_directory = Path.home()

    # Windows normally uses the Downloads directory under the user profile.
    if OPERATING_SYSTEM == "Windows":
        return home_directory / "Downloads"

    # Linux: Read the XDG user directory configuration.
    xdg_config_file = (
        home_directory / ".config" / "user-dirs.dirs"
    )

    if xdg_config_file.is_file():

        try:
            with xdg_config_file.open(
                "r",
                encoding="utf-8",
            ) as config_file:

                for line in config_file:

                    line = line.strip()

                    if not line.startswith("XDG_DOWNLOAD_DIR="):
                        continue

                    value = line.split("=", 1)[1].strip()

                    # Remove surrounding quotes.
                    if (
                        len(value) >= 2
                        and value[0] == '"'
                        and value[-1] == '"'
                    ):
                        value = value[1:-1]

                    # Expand environment variables such as $HOME.
                    value = os.path.expandvars(value)

                    # Expand ~ if present.
                    downloads_path = Path(
                        os.path.expanduser(value)
                    )

                    if not downloads_path.is_absolute():
                        downloads_path = (
                            home_directory / downloads_path
                        )

                    return downloads_path

        except (OSError, ValueError) as error:
            print(
                "[WARNING] Could not read Linux Downloads "
                f"configuration: {error}"
            )

    # Default fallback.
    return home_directory / "Downloads"


DOWNLOADS_FOLDER = get_downloads_folder()

LOG_FILE = DOWNLOADS_FOLDER / LOG_FILE_NAME


# ============================================================================
# Logging Configuration
# ============================================================================

logger = logging.getLogger("DownloadsCleanup")
logger.setLevel(logging.INFO)

# Avoid duplicate messages when imported by another module.
logger.propagate = False


def configure_logging() -> None:
    """
    Configure rotating file logging.

    Normally, the log is stored in the Downloads directory.

    If that directory does not exist, use the user's home directory
    for logging so the missing Downloads directory can still be reported.
    """

    if logger.handlers:
        return

    if DOWNLOADS_FOLDER.is_dir():
        log_path = LOG_FILE
    else:
        log_path = Path.home() / LOG_FILE_NAME

    log_handler = RotatingFileHandler(
        filename=log_path,
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_LOG_COUNT,
        encoding="utf-8",
    )

    log_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        )
    )

    logger.addHandler(log_handler)


# ============================================================================
# Helper Functions
# ============================================================================

def print_and_log(message: str, level: str = "info") -> None:
    """
    Print a message to the console and write it to the log.

    Supported levels:
        info
        warning
        error
    """

    print(message)

    log_function = getattr(logger, level, logger.info)
    log_function(message)


def is_cleanup_log(file_path: Path) -> bool:
    """
    Identify the main cleanup log and its rotated backup files.

    This prevents the cleanup utility from moving its own logs to Trash.
    """

    return (
        file_path.name == LOG_FILE_NAME
        or file_path.name.startswith(LOG_FILE_NAME + ".")
    )


# ============================================================================
# Cleanup Logic
# ============================================================================

def cleanup_downloads() -> None:
    """
    Scan the Downloads folder and identify old files.

    DRY_RUN:
        Report qualifying files without moving them.

    LIVE:
        Move qualifying files to the operating system's Trash.
    """

    configure_logging()

    # ========================================================================
    # Verify Downloads Folder
    # ========================================================================

    if not DOWNLOADS_FOLDER.is_dir():

        message = (
            f"[ERROR] Downloads folder does not exist: "
            f"{DOWNLOADS_FOLDER}"
        )

        logger.error(message)
        print(message)

        raise SystemExit(1)

    # ========================================================================
    # Calculate Cutoff Date
    # ========================================================================

    cutoff_date = datetime.now() - timedelta(
        days=FILE_AGE_DAYS
    )

    # ========================================================================
    # Determine Current Mode
    # ========================================================================

    if DRY_RUN:
        mode = "DRY RUN - NO FILES WILL BE MOVED"
    else:
        mode = f"LIVE RUN - FILES WILL BE MOVED TO {TRASH_NAME}"

    # ========================================================================
    # Startup Information
    # ========================================================================

    print("=" * 75)
    print("Cross-Platform Downloads Cleanup")
    print("=" * 75)
    print(f"Operating system : {OPERATING_SYSTEM}")
    print(f"Current mode     : {mode}")
    print(f"Downloads folder : {DOWNLOADS_FOLDER}")
    print(f"File age limit   : {FILE_AGE_DAYS} days")
    print(f"Cutoff date      : {cutoff_date}")
    print(f"Log file         : {LOG_FILE}")
    print("=" * 75)

    logger.info("=" * 75)
    logger.info("Downloads cleanup started")
    logger.info("Operating system: %s", OPERATING_SYSTEM)
    logger.info("Downloads folder: %s", DOWNLOADS_FOLDER)
    logger.info("File age limit: %d days", FILE_AGE_DAYS)
    logger.info("Cutoff date: %s", cutoff_date)
    logger.info("Mode: %s", mode)
    logger.info("Destination: %s", TRASH_NAME)
    logger.info("=" * 75)

    # ========================================================================
    # Counters
    # ========================================================================

    files_scanned = 0
    old_files = 0
    files_moved = 0
    errors = 0

    # ========================================================================
    # Scan Downloads Folder
    # ========================================================================

    try:

        for file_path in DOWNLOADS_FOLDER.iterdir():

            # ---------------------------------------------------------------
            # Skip directories and non-files
            # ---------------------------------------------------------------

            try:
                if not file_path.is_file():
                    continue

            except OSError as error:
                errors += 1

                logger.error(
                    "FAILED TO CHECK FILE | Name: %s | Error: %s",
                    file_path.name,
                    error,
                )

                continue

            # ---------------------------------------------------------------
            # Skip cleanup logs and rotated backups
            # ---------------------------------------------------------------

            if is_cleanup_log(file_path):
                continue

            files_scanned += 1

            # ===============================================================
            # Process File
            # ===============================================================

            try:

                # -----------------------------------------------------------
                # Get Last Modification Time
                # -----------------------------------------------------------

                modification_timestamp = file_path.stat().st_mtime

                modification_time = datetime.fromtimestamp(
                    modification_timestamp
                )

                formatted_modified_time = (
                    modification_time.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                )

                # -----------------------------------------------------------
                # Check File Age
                # -----------------------------------------------------------

                if modification_time >= cutoff_date:
                    continue

                old_files += 1

                # ===========================================================
                # DRY RUN
                # ===========================================================

                if DRY_RUN:

                    message = (
                        f"[WOULD MOVE] {file_path.name} | "
                        f"Last modified: {formatted_modified_time}"
                    )

                    print_and_log(message)

                # ===========================================================
                # LIVE RUN
                # ===========================================================

                else:

                    try:

                        # Send the file to the OS-specific Trash.
                        #
                        # Windows: Recycle Bin
                        # Linux: Desktop Trash

                        send2trash(str(file_path))

                        recycle_time = datetime.now()

                        formatted_recycle_time = (
                            recycle_time.strftime(
                                "%Y-%m-%d %H:%M:%S"
                            )
                        )

                        files_moved += 1

                        message = (
                            f"[MOVED TO {TRASH_NAME.upper()}] "
                            f"{file_path.name} | "
                            f"Last modified: "
                            f"{formatted_modified_time} | "
                            f"Action time: {formatted_recycle_time}"
                        )

                        print_and_log(message)

                    except Exception as error:

                        errors += 1

                        message = (
                            f"[ERROR] Failed to move "
                            f"{file_path.name}: {error}"
                        )

                        print(message)

                        logger.error(
                            "FAILED TO MOVE | "
                            "Name: %s | Error: %s",
                            file_path.name,
                            error,
                        )

            # ===============================================================
            # File Processing Error
            # ===============================================================

            except Exception as error:

                errors += 1

                message = (
                    f"[ERROR] Could not process "
                    f"{file_path.name}: {error}"
                )

                print(message)

                logger.error(
                    "FAILED TO PROCESS | "
                    "Name: %s | Error: %s",
                    file_path.name,
                    error,
                )

    # ========================================================================
    # Directory Scan Error
    # ========================================================================

    except OSError as error:

        errors += 1

        message = (
            f"[ERROR] Could not scan Downloads folder: {error}"
        )

        print(message)

        logger.exception(
            "Could not scan Downloads folder"
        )

    # ========================================================================
    # Summary
    # ========================================================================

    print()
    print("=" * 75)
    print("Cleanup Summary")
    print("=" * 75)

    print(f"Operating system: {OPERATING_SYSTEM}")
    print(f"Files scanned: {files_scanned}")
    print(f"Files older than {FILE_AGE_DAYS} days: {old_files}")

    if DRY_RUN:

        print(f"Files that would be moved: {old_files}")
        print("Files actually moved: 0")
        print("DRY RUN completed. No files were moved.")

    else:

        print(f"Files moved to {TRASH_NAME}: {files_moved}")

    print(f"Errors encountered: {errors}")
    print("=" * 75)

    # ========================================================================
    # Log Summary
    # ========================================================================

    logger.info("=" * 75)

    logger.info(
        "Cleanup completed | "
        "OS: %s | "
        "Files scanned: %d | "
        "Old files: %d | "
        "Files moved: %d | "
        "Errors: %d",
        OPERATING_SYSTEM,
        files_scanned,
        old_files,
        files_moved,
        errors,
    )

    if DRY_RUN:
        logger.info(
            "DRY RUN COMPLETED | No files were moved."
        )

    logger.info("=" * 75)


# ============================================================================
# Program Entry Point
# ============================================================================

if __name__ == "__main__":

    try:
        cleanup_downloads()

    except KeyboardInterrupt:

        print()
        print("[CANCELLED] Cleanup interrupted by user.")

        logger.warning(
            "Cleanup interrupted by user."
        )

    except SystemExit:
        raise

    except Exception as error:

        # Attempt to initialize logging if startup failed early.
        if not logger.handlers:
            try:
                configure_logging()
            except Exception:
                pass

        logger.exception(
            "Unexpected application error: %s",
            error,
        )

        print(
            f"[CRITICAL ERROR] "
            f"Unexpected application error: {error}"
        )

        raise SystemExit(1)