import time

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Shows (or deletes with --delete) uploaded tracks that are older than the given number of hours'

    def add_arguments(self, parser):
        parser.add_argument('--hours', type=int, default=24, help='age of the files, 24 by default')
        parser.add_argument('--delete', action='store_true', help='really delete the files')

    def handle(self, *args, **options):
        media_root = settings.MEDIA_ROOT
        if not media_root.exists():
            self.stdout.write('The media folder does not exist.')
            return

        limit = time.time() - options['hours'] * 3600
        old_files = [path for path in media_root.iterdir() if path.is_file() and path.stat().st_mtime < limit]

        for path in old_files:
            if options['delete']:
                path.unlink()
            self.stdout.write(('deleted: ' if options['delete'] else 'old file: ') + path.name)

        if not old_files:
            self.stdout.write('No old files.')
        elif not options['delete']:
            self.stdout.write('Nothing was deleted. Add --delete to remove these files.')
