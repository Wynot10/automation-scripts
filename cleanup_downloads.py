"""
Windows Downloads Cleanup Script

Purpose:
- Scans the current user's Downloads folder.
- Finds files older than FILE_AGE_DAYS based on last modification time.
- In DRY_RUN mode, only reports files that would be moved.
- In LIVE mode, moves qualifying files to the Windows Recycle Bin.
- Logs file name, modification date/time, and action taken.
- Automatically rotates the log file when it reaches 5 MB.

Requirements:
- Windows OS
- Python 3.x
- Send2Trash

Install dependency:
    python -m pip install Send2Trash
"""

from pathlib import Path
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from send2trash import send2trash
import logging


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
#   LIVE RUN - qualifying files are moved to the Recycle Bin.
DRY_RUN = True

# Maximum log file size: 5 MB.
MAX_LOG_SIZE = 5 * 1024 * 1024

# Number of backup log files to keep.
#
# Example:
#   downloads_cleanup.log
#   downloads_cleanup.log.1
#   downloads_cleanup.log.2
#   ...
BACKUP_LOG_COUNT = 5

# Current user's Downloads folder.
DOWNLOADS_FOLDER = Path.home() / "Downloads"

# Main log file.
LOG_FILE = DOWNLOADS_FOLDER / "downloads_cleanup.log"


# ============================================================================
# Logging Configuration
# ============================================================================

logger = logging.getLogger("DownloadsCleanup")
logger.setLevel(logging.INFO)

# Prevent duplicate log messages if this module is imported elsewhere.
logger.propagate = False

# Only configure the handler once.
if not logger.handlers:

    log_handler = RotatingFileHandler(
        LOG_FILE,
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
# Cleanup Logic
# ============================================================================

def cleanup_downloads():
    """
    Scan the Downloads folder and identify files older than FILE_AGE_DAYS.

    If DRY_RUN is True:
        Files are only reported and logged.

    If DRY_RUN is False:
        Files are moved to the Windows Recycle Bin.
    """

    # ========================================================================
    # Verify Downloads Folder Exists
    # ========================================================================

    if not DOWNLOADS_FOLDER.exists():
        logger.error(
            "Downloads folder does not exist: %s",
            DOWNLOADS_FOLDER,
        )

        print(
            f"[ERROR] Downloads folder does not exist: "
            f"{DOWNLOADS_FOLDER}"
        )

        raise SystemExit(1)

    # ========================================================================
    # Calculate Cutoff Date
    # ========================================================================

    cutoff_date = datetime.now() - timedelta(days=FILE_AGE_DAYS)

    # ========================================================================
    # Determine Current Mode
    # ========================================================================

    if DRY_RUN:
        mode = "DRY RUN - NO FILES WILL BE MOVED"
    else:
        mode = "LIVE RUN - FILES WILL BE MOVED TO THE RECYCLE BIN"

    # ========================================================================
    # Display Startup Information
    # ========================================================================

    print("=" * 70)
    print("Downloads Cleanup")
    print("=" * 70)
    print(f"Current mode : {mode}")
    print(f"Downloads    : {DOWNLOADS_FOLDER}")
    print(f"Age limit    : {FILE_AGE_DAYS} days")
    print(f"Cutoff date  : {cutoff_date}")
    print("=" * 70)

    logger.info("=" * 70)
    logger.info("Downloads cleanup started")
    logger.info("Downloads folder: %s", DOWNLOADS_FOLDER)
    logger.info("File age limit: %d days", FILE_AGE_DAYS)
    logger.info("Cutoff date: %s", cutoff_date)
    logger.info("Current mode: %s", mode)
    logger.info("=" * 70)

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
        directory_entries = DOWNLOADS_FOLDER.iterdir()

        for file_path in directory_entries:

            # ----------------------------------------------------------------
            # Skip directories
            # ----------------------------------------------------------------

            if not file_path.is_file():
                continue

            # ----------------------------------------------------------------
            # Skip the cleanup log itself
            #
            # Use resolve() because file_path.name is a string while
            # LOG_FILE is a Path object.
            # ----------------------------------------------------------------

            try:
                if file_path.resolve() == LOG_FILE.resolve():
                    continue
            except OSError:
                # If the path cannot be resolved, continue processing it.
                pass

            files_scanned += 1

            # =================================================================
            # Process File
            # =================================================================

            try:

                # -------------------------------------------------------------
                # Get Last Modification Time
                # -------------------------------------------------------------

                modification_timestamp = file_path.stat().st_mtime

                modification_time = datetime.fromtimestamp(
                    modification_timestamp
                )

                formatted_modified_time = (
                    modification_time.strftime("%Y-%m-%d %H:%M:%S")
                )

                # -------------------------------------------------------------
                # Determine Whether File Is Old Enough
                # -------------------------------------------------------------

                if modification_time >= cutoff_date:
                    continue

                old_files += 1

                # =============================================================
                # DRY RUN
                # =============================================================

                if DRY_RUN:

                    print(
                        f"[WOULD MOVE] {file_path.name} | "
                        f"Last modified: {formatted_modified_time}"
                    )

                    logger.info(
                        "DRY RUN | WOULD MOVE | "
                        "Name: %s | Last modified: %s",
                        file_path.name,
                        formatted_modified_time,
                    )

                # =============================================================
                # LIVE RUN
                # =============================================================

                else:

                    try:

                        # -----------------------------------------------------
                        # Move File to Windows Recycle Bin
                        # -----------------------------------------------------

                        send2trash(str(file_path))

                        recycle_time = datetime.now()

                        formatted_recycle_time = (
                            recycle_time.strftime("%Y-%m-%d %H:%M:%S")
                        )

                        files_moved += 1

                        print(
                            f"[MOVED] {file_path.name} | "
                            f"Last modified: {formatted_modified_time} | "
                            f"Recycle time: {formatted_recycle_time}"
                        )

                        logger.info(
                            "MOVED TO RECYCLE BIN | "
                            "Name: %s | "
                            "Last modified: %s | "
                            "Recycle time: %s",
                            file_path.name,
                            formatted_modified_time,
                            formatted_recycle_time,
                        )

                    except Exception as error:

                        errors += 1

                        print(
                            f"[ERROR] Failed to move "
                            f"{file_path.name}: {error}"
                        )

                        logger.error(
                            "FAILED TO MOVE | "
                            "Name: %s | Error: %s",
                            file_path.name,
                            error,
                        )

            # =================================================================
            # File Processing Error
            # =================================================================

            except Exception as error:

                errors += 1

                print(
                    f"[ERROR] Could not process "
                    f"{file_path.name}: {error}"
                )

                logger.error(
                    "FAILED TO PROCESS | "
                    "Name: %s | Error: %s",
                    file_path.name,
                    error,
                )

    # =========================================================================
    # Directory Scan Error
    # =========================================================================

    except Exception as error:

        errors += 1

        print(
            f"[ERROR] Could not scan Downloads folder: {error}"
        )

        logger.exception(
            "Could not scan Downloads folder: %s",
            error,
        )

    # =========================================================================
    # Summary
    # =========================================================================

    print()
    print("=" * 70)
    print("Cleanup Summary")
    print("=" * 70)
    print(f"Files scanned:                 {files_scanned}")
    print(f"Files older than {FILE_AGE_DAYS} days:   {old_files}")

    if DRY_RUN:

        print(f"Files that WOULD MOVE:         {old_files}")
        print("Files actually moved:          0")
        print("No files were actually moved.")

    else:

        print(f"Files moved to Recycle Bin:    {files_moved}")
        print(f"Errors encountered:            {errors}")

    print("=" * 70)

    # =========================================================================
    # Log Summary
    # =========================================================================
    logger.info("=" * 70)
    logger.info(
        "Cleanup completed | "
        "Files scanned: %d | "
        "Old files: %d | "
        "Files moved: %d | "
        "Errors: %d",
        files_scanned,
        old_files,
        files_moved,
        errors,
    )

    if DRY_RUN:
        logger.info(
            "DRY RUN COMPLETED | "
            "No files were actually moved."
        )

    logger.info("=" * 70)


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

    except Exception as error:

        logger.exception(
            "Unexpected application error: %s",
            error,
        )

        print(
            f"[CRITICAL ERROR] "
            f"Unexpected application error: {error}"
        )

