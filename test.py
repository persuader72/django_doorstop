import time
import gzip


gf = gzip.GzipFile('/tmp/pippo.zip', mode='wb', compresslevel=9)
gf.write(b'A')
gf.close()