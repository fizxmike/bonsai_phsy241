
from subprocess import call
import struct
import glob
import numpy as np
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d import axes3d

#assume this Bonsai and bonsai_phys241 are next to eachother
BONSAI_BIN = '../Bonsai/runtime/bonsai2_slowdust'

class Stars(object):

	def __init__(self,fileObj,dim,count):
		#pass the file pointer to this function for each particle
		self.mass = np.zeros((count),dtype=np.float32)
		self.pos = np.zeros((count,dim),dtype=np.float32)
		self.vel = np.zeros((count,dim),dtype=np.float32)
		self.metals = np.zeros((count),dtype=np.float32)

		if dim == 3:
			#3D
			for i in range(count):
				mass,x1,x2,x3,v1,v2,v3,metals,tform_IGNORED,eps_IGNORED,phi_IGNORED = struct.unpack('f3f3f3fi',fileObj.read(44))
				self.pos[i,:] = (x1,x2,x3)
				self.vel[i,:] = (v1,v2,v3)
				self.mass[i] = mass
				self.metals[i] = metals

		else:
			raise Exception("%iD not supported"%dim)



def run_plummer(nParticles,snap_prefix,T=2,dt=0.0625, dSnap = 0.0625, bonsai_bin = None, mpi_n = 0, mpi_log_file = 'mpiout.log'):
	
	if bonsai_bin is None:
		#use default
		bonsai_bin = BONSAI_BIN

	log = False

	if mpi_n > 0:
		#run mpi
		#mpirun -n 2 --output-filename mpiout.txt ./bonsai2_slowdust -i model3_child_compact.tipsy -T1000 --logfile logfile.txt
		if call(['mpirun','-n',str(mpi_n),
				 '--output-filename',mpi_log_file,bonsai_bin,
				 '--plummer',str(nParticles),
				 '--snapname',snap_prefix,'--snapiter','1',
				 '-T',str(T),'-dt',str(dt)
				]):
			return "Error"
		else:
			return "Done"

	else:
		#single GPU mode
		if call([bonsai_bin,'--log' if log else '','--plummer',str(nParticles),'--snapname',snap_prefix,'--snapiter',str(dSnap),'-T',str(T),'-dt',str(dt)]):
			return "Error"
		else:
			return "Done"

def run_sphere(nParticles,snap_prefix,T=2,dt=0.0625,dSnap = 0.0625):
	log = False

	if call([BONSAI_BIN,'--log' if log else '','--sphere',str(nParticles),'--snapname',snap_prefix,'--snapiter',str(dSnap),'-T',str(T),'-dt',str(dt)]):
		return "Error"
	else:
		return "Done"

def fig_gen(stars, index, prefix='', lim = .8, figsize = 10, pointsize = .75):
		fig = plt.figure(figsize=(figsize,figsize))
		ax = fig.gca(projection='3d')
		ax.plot(stars.pos[:,0],stars.pos[:,1],stars.pos[:,2],'w.',markersize=pointsize)
		ax.set_xlim(-lim,lim)
		ax.set_ylim(-lim,lim)
		ax.set_zlim(-lim,lim)
		ax.set_axis_off()
		ax.set_axis_bgcolor('black')
		plt.tight_layout()
		fig_path_string = prefix+'pos_'+str(index)+'.png'
		plt.savefig(fig_path_string)
		print fig_path_string


def snap_figs(snap_array, prefix=''):	
    counter = 0

    for snap in snap_array:
		fig_gen(snap['star'], prefix, counter)
		counter +=1

def load_tipsy(tipsy_prefix, figures_prefix = None):
	'''pass figures_prefix to generate figures on the fly (does not populate snaps_array)'''

	#comparitor for file name sorting
	def cmp(x,y):
		x_num = float(x.lstrip(tipsy_prefix))
		y_num = float(y.lstrip(tipsy_prefix))
		if x_num > y_num:
			return 1
		elif x_num < y_num:
			return -1
		else:
			return 0
	
	tipsy_list = glob.glob(tipsy_prefix+"*")
	
	tipsy_list.sort(cmp)

	snaps_array = []

	index = 0

	for tipsy_file in tipsy_list:
		#make sure path is file

		tfile = open(tipsy_file,'rb')

		print 'Loading Header (%s):' % tipsy_file

		#get time
		time = struct.unpack('d',tfile.read(8)) #one double

		print "Simulation Time: %f" % time
		
		snaps_array.append({'time':time,'gas':[],'dark':[],'star':[]})

		#get number of each particle
		#nTot,nDim,nGas,nDark,nStar = struct.unpack('iiiii',tfile.read(20))
		nTot,nDim,nGas,nDark,nStar,temp = struct.unpack('iiiiii',tfile.read(24))
		print "nTot: %i, nDim: %i, nGas: %i, nDark: %i, nStar: %i" % (nTot, nDim, nGas, nDark, nStar)




		#process stars:
		if nStar > 0:
			if figures_prefix is not None:
				fig_gen(Stars(tfile,nDim,nStar),index,prefix=figures_prefix)
			else:
				snaps_array[-1]['star'] = Stars(tfile,nDim,nStar)

		tfile.close()

		index += 1

	return snaps_array