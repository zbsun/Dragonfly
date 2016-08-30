#!/usr/bin/env python

'''
Convert h5 files generated by Chuck for the SPI

Needs:
    <h5_fname> - Path to photon-converted h5 file used in SPI
    <selection_file> - Either .txt or .h5 file containing information used for
                       selecting single hits

Produces:
    EMC file with all the single hits in the h5 file
'''

import os
import numpy as np
import h5py
import sys
#Add utils directory to pythonpath
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from py_src import writeemc

if len(sys.argv) < 3:
    print "Format: %s <h5_fname> <selection_file>" % sys.argv[0]
    print "\tOptional: <binning>"
    sys.exit(1)

if not os.path.isfile(sys.argv[1]):
    print 'Data file %s not found. Exiting.' % sys.argv[1]
    print
    sys.exit()

binsize = 1
def binimg(array, binsize):
	s = array.shape
	out = array.reshape(s[0]/binsize, binsize, s[1]/binsize, binsize).sum(axis=(1,3))
	return out

extension = os.path.splitext(sys.argv[2])[1]
if extension == '.txt':
    print 'Selection file is text file'
    tag = 'txt'
    run = int(os.path.basename(sys.argv[1]).split('_')[1])
    lines = np.loadtxt(sys.argv[2], dtype='i4')
    ind = lines[lines[:,0] == run][:,1]
elif extension == '.h5':
    print 'Selection file is h5 file'
    tag = 'h5'
    yf = h5py.File(sys.argv[1], 'r')
    cf = h5py.File(sys.argv[2], 'r')
    cls = cf['hitClass/class'][:].flatten()
    yt = yf['dataPhotons/eventTime'][:]
    ct = cf['hitClass/timestamps'][:][cls==1]
    cf.close()
    yf.close()

    ytsort = np.argsort(yt)
    ytrank = np.searchsorted(yt, ct, sorter=ytsort)

    ytranksel = ytrank[(ytrank<len(yt)) & (ytrank>0)]
    ctsel = ct[(ytrank<len(yt)) & (ytrank>0)]
    num = ytsort[ytranksel]
    num1 = ytsort[ytranksel-1]
    ind = np.concatenate([num[yt[num]-ctsel<1e6], num1[ctsel-yt[num1]<1e6]])
ind.sort()
print ind.shape, 'single hits'

if len(sys.argv) > 3:
    binsize = int(sys.argv[3])
    tag += '_%d' % binsize

f = h5py.File(sys.argv[1], 'r')
num_frames = f['dataPhotons/back/index'].shape[0]
print num_frames, "frames in h5 file"
index = f['dataPhotons/back/index']
count = f['dataPhotons/back/photonCount']
ix = f['dataPhotons/back/iX'][:].flatten()
iy = f['dataPhotons/back/iY'][:].flatten()

emcwriter = writeemc.EMC_writer('data/%s_%s.emc' % (os.path.splitext(os.path.basename(sys.argv[1]))[0], tag),
                                1028*1040/binsize/binsize)

j = 0
for i in ind:
    pattern = np.zeros((1028,1040), dtype='i4')
    place = index[i]
    pattern[iy[place], ix[place]] = count[i]
    if binsize > 1:
        pattern = binimg(pattern, binsize)
    
    emcwriter.write_frame(pattern.flatten())
    sys.stderr.write('\rFinished %d/%d' % (j+1, len(ind)))
    j += 1

f.close()
sys.stderr.write('\n')
emcwriter.finish_write()