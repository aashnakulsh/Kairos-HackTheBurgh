"""Small on-demand GDELT archive cache. Event dates and report dates stay distinct."""
import csv
from datetime import date
import io
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError
from uuid import uuid4
import zipfile


class EventArchive:
    def __init__(self, root, transport=None):
        self.root = Path(root)/'raw/gdelt'
        self.root.mkdir(parents=True, exist_ok=True)
        self.transport = transport or urlopen

    def events(self, day, cutoff, limit=12):
        stamp=date.fromisoformat(day).strftime('%Y%m%d')
        if day >= cutoff: return []
        path=self.root/f'{stamp}.export.CSV.zip'
        if not path.exists():
            try:
                with self.transport('https://data.gdeltproject.org/events/'+path.name,timeout=12) as response:
                    body=response.read(30_000_001)
                if len(body)>30_000_000 or not zipfile.is_zipfile(io.BytesIO(body)): return []
                temp=path.with_suffix('.'+uuid4().hex+'.download')
                temp.write_bytes(body); temp.replace(path)
            except (OSError,URLError,TimeoutError): return []
        try:
            with zipfile.ZipFile(path) as archive:
                entry=next((e for e in archive.infolist() if not e.is_dir() and e.file_size<150_000_000),None)
                if entry is None:return []
                found=[]
                with archive.open(entry) as stream:
                    for row in csv.reader(io.TextIOWrapper(stream,encoding='utf-8-sig'),delimiter='\t'):
                        if len(row)!=58 or row[1]!=stamp or not row[-1].startswith(('https://','http://')):continue
                        found.append(dict(event_date=day,report_archive_date=day,record_id=row[0],source_url=row[-1]))
                        if len(found)>=limit:break
                return found
        except (OSError,zipfile.BadZipFile,UnicodeError):return []
