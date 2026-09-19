"""Verify the release and restore SQLite/JSONL, using Python 3 standard library only."""
from pathlib import Path
import json,hashlib,gzip,shutil,argparse,io
ROOT=Path(__file__).resolve().parent.parent
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
class Parts(io.RawIOBase):
 def __init__(self,paths):self.paths=iter(paths);self.current=None
 def readable(self):return True
 def readinto(self,b):
  while True:
   if self.current is None:
    p=next(self.paths,None)
    if p is None:return 0
    self.current=p.open('rb')
   n=self.current.readinto(b)
   if n:return n
   self.current.close();self.current=None
 def close(self):
  if self.current:self.current.close()
  super().close()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--verify-only',action='store_true');args=ap.parse_args()
 manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf8'))
 for r in manifest['files']:
  p=ROOT/r['path']
  if not p.is_file() or p.stat().st_size!=r['bytes'] or digest(p)!=r['sha256']:raise SystemExit('Checksum failed: '+r['path'])
 meta=json.loads((ROOT/'data/dataset.json').read_text(encoding='utf8'))
 for item in meta['files']:
  target=ROOT/'restored'/item['name'];output=None;h=hashlib.sha256();size=0
  if not args.verify_only:
   target.parent.mkdir(exist_ok=True)
   if target.exists():
    if digest(target)==item['sha256']:print('Already restored:',item['name']);continue
    raise SystemExit('Existing file differs; preserved: '+str(target))
   output=target.with_suffix(target.suffix+'.partial').open('xb')
  try:
   parts=[ROOT/p for p in item['parts']]
   streams=[gzip.open(p,'rb') for p in parts] if item['format']=='independent-jsonl-gzip' else [gzip.GzipFile(fileobj=io.BufferedReader(Parts(parts)),mode='rb')]
   for stream in streams:
    with stream:
     for b in iter(lambda:stream.read(1024*1024),b''):
      h.update(b);size+=len(b)
      if output:output.write(b)
  finally:
   if output:output.close()
  assert h.hexdigest()==item['sha256'] and size==item['bytes'], 'Restored content mismatch'
  if output:target.with_suffix(target.suffix+'.partial').rename(target)
  print('Verified:',item['name'],size,'bytes')
 print('All release files and both original datasets verified.')
if __name__=='__main__':main()
