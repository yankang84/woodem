# encoding: utf-8
from woo import utils,pack
from woo.core import *
from woo.dem import *
from woo.pre import *
import woo.plot
import math
import os.path
from minieigen import *
import sys
import cStringIO as StringIO
import numpy
import pprint
nan=float('nan')


import woo.pyderived
class Roro(woo.core.Preprocessor,woo.pyderived.PyWooObject):
	'Preprocessor for the Rollenrost simulation'
	_classTraits=None
	PAT=woo.pyderived.PyAttrTrait
	_attrTraits=[
		PAT(float,'cylLenReal',2,unit='m',startGroup="General",doc="Length of cylinders"),
		PAT(float,'cylLenSim',.1,unit='m',doc="Simulated length of cylinders"), 
		PAT(float,'cylRelLen',nan,noGui=True,doc="Relative length of simulated cylinders"), # set when called
		PAT(float,'massFlowRate',100,unit="t/h",doc="Incoming mass flow rate (considering real length of the screen)"),
		PAT(float,'conveyorHt',.05,unit='m',doc="Height of particle layor on the conveyor"),
		PAT(float,'time',2,unit='s',doc="Time of the simulation (after reaching steady state); if non-positive, don't wait for steady state, use *mass* instead."),
		PAT(float,'mass',0,unit='kg',doc="Total feed mass; if non-positive, don't limit generated mass, simulate *time* of steady state instead"),

		# Cylinders
		PAT([Vector3,],'cylXzd',[],startGroup="Cylinders",unit='mm',doc="Coordinates and diameters of cylinders. If empty, *cylNum*, *cylDiameter*, *inclination* and *gap* are used to compute coordinates automatically"),
		PAT(float,'angVel',2*math.pi,unit='rot/min',doc="Angular velocity of cylinders"),
		PAT(int,'cylNum',6,"Number of cylinders (only used when cylXzd is empty)"),
		PAT(float,'cylDiameter',.085,unit='mm',altUnits=[("in",1/0.0254),],doc="Diameter of cylinders (only used when cylXzd is empty)"),
		PAT(float,'inclination',math.radians(15),unit="deg",doc="Inclination of cylinder plane (only used when cylXzd is empty)"),
		PAT(float,'gap',.01,unit="mm",doc="Gap between cylinders (computed automatically if cylXzd is given)"),
		PAT([float,],'gaps',[],unit="mm",doc="Variable gaps between cylinders; if given, the value of *gap* and *cylNum* is not used for creating cylinder coordinates"),

		# feed
		PAT([Vector2,],'psd',[Vector2(0.005,.0),Vector2(.01,.2),Vector2(.02,1.)],startGroup="Pellets",unit=['mm','%'],doc="Particle size distribution of generated particles: first value is diameter, second value is cummulative fraction"),
		PAT(woo.dem.PelletMat,'material',woo.dem.PelletMat(density=3200,young=1e5,ktDivKn=.2,tanPhi=math.tan(.5),normPlastCoeff=50,kaDivKn=0.),"Material of particles"),
		PAT(woo.dem.PelletMat,'cylMaterial',None,"Material of cylinders (if not given, material for particles is used for cylinders)"),
		PAT(woo.dem.PelletMat,'plateMaterial',None,"Material of plates (if not given, material for cylinders is used for cylinders)"),

		# Outputs
		PAT(str,'reportFmt',"/tmp/{tid}.xhtml",startGroup="Outputs",doc="Report output format (Scene.tags can be used)."),
		PAT(str,'feedCacheDir',".","Directory where to store pre-generated feed packings"),
		PAT(str,'saveFmt',"/tmp/{tid}-{stage}.bin.gz","Savefile format; keys are :ref:`Scene.tags` and additionally ``{stage}`` will be replaced by 'init', 'steady' and 'done'."),
		PAT(int,'backupSaveTime',1800,"How often to save backup of the simulation (0 or negative to disable)"),
		PAT(float,'vtkFreq',4,"How often should VtkExport run, relative to *factStepPeriod*. If negative, run never."),
		PAT(str,'vtkPrefix',"/tmp/{tid}-","Prefix for saving VtkExport data; formatted with ``format()`` providing :ref:`Scene.tags` as keys."),
		PAT([str,],'reportHooks',[],noGui=True,doc="Python expressions returning a 3-tuple with 1. raw HTML to be included in the report, 2. list of (figureName,matplotlibFigure) to be included in figures, 3. dictionary to be added to the 'custom' dict saved in the database."),

		# Tunables
		PAT(int,'factStepPeriod',800,startGroup="Tunables",doc="Run factory (and deleters) every *factStepPeriod* steps."),
		PAT(float,'pWaveSafety',.7,"Safety factor for critical timestep"),
		PAT(str,'variant',"plain",choice=["plain","customer1","customer2"],doc="Geometry of the feed and possibly other specific details"),
		PAT(float,'gravity',10.,unit='m/s²',doc="Gravity acceleration magnitude"),
		PAT(Vector2,'quivAmp',Vector2(.0,.0),unit="mm",doc="Cylinder quiver amplitudes (horizontal and vertical), relative to cylinder radius"),
		PAT(Vector3,'quivHPeriod',Vector3(3000,5000,3),"Horizontal quiver period (relative to Δt); assigned quasi-randomly from the given range, with z-component giving modulo divisor"),
		PAT(Vector3,'quivVPeriod',Vector3(5000,11000,5),"Vertical quiver period (relative to Δt); assigned quasi-randomly from the given range, with z-component giving modulo divisor"),
		PAT(float,'steadyFlowFrac',1.,"Start steady (measured) phase when efflux (fall over, apertures, out-of-domain) reaches this fraction of influx (feed); only used when *time* is given"),
		PAT(float,'residueFlowFrac',.02,"Stop simulation once delete rate drops below this fraction of the original feed rate (after the requested :ref:`mass` has been generated); only used when *mass* is given."),
		PAT(float,'rateSmooth',.2,"Smoothing factor for plotting rates in factory and deleters"),
		PAT(Vector2,'thinningCoeffs',Vector2(0,.8),"Parameters for plastic thinning: first component is :ref:`Law2_L6Geom_PelletPhys_Pellet.thinningFactor`, the other is :ref:`Law2_L6Geom_PelletPhys_Pellet.rMinFrac`."),
		PAT([int,],'buckets',[],"Collect particles from several apertures together; each numer specifies how much apertures is taken; invalid values (past the number of cylinders) are simply ignored"),
		PAT([float,],'efficiencyGapFrac',[.9,1.,1.1,1.2,1.3],"Diameters relative to :ref:`gap` for which the sieving efficiency is determined."),
	]
	def __init__(self,**kw):
		Preprocessor.__init__(self)
		self.wooPyInit(Roro,Preprocessor,**kw)
	def __call__(self):
		import woo.pre.roro
		self.cylRelLen=self.cylLenSim/self.cylLenReal;
		return woo.pre.roro.run(self)


def ySpannedFacets(xx,yy,zz,shift=True,halfThick=0.,**kw):
	if halfThick!=0.:
		if shift:
			A,B=Vector2(xx[0],zz[0]),Vector2(xx[1],zz[1])
			dx,dz=Vector2(-(B[1]-A[1]),B[0]-A[0]).normalized()*halfThick
			xx,zz=[x+dx for x in xx],[z+dz for z in zz]
		kw['halfThick']=halfThick # copy arg
	A,B,C,D=(xx[0],yy[0],zz[0]),(xx[1],yy[0],zz[1]),(xx[0],yy[1],zz[0]),(xx[1],yy[1],zz[1])
	return [utils.facet(vertices,**kw) for vertices in (A,B,C),(C,B,D)]

def run(pre): # use inputs as argument
	print 'roro.run()'
	#print 'Input parameters:'
	#print pre.dumps(format='expr',noMagic=True)
	#print pre.dumps(format='html',fragment=True)
	import woo.config

	s=Scene()
	de=DemField()
	s.fields=[de]

	if pre.variant not in ('plain','customer1','customer2'): raise ValueError("Roro.variant must be one of 'plain', 'customer1', 'customer2' (not '%s')"%pre.variant)
	if pre.gap<0: raise ValueError("Roro.gap must be positive (are cylinders overlapping?)")
	if (pre.time>0 and pre.mass>0) or (pre.time<=0 and pre.mass<=0): raise ValueError("Exactly one of Roro.time or Roro.mass must be positive.")

	for a in ['reportFmt','feedCacheDir','saveFmt','vtkPrefix']: setattr(pre,a,utils.fixWindowsPath(getattr(pre,a)))

	if not pre.cylMaterial: pre.cylMaterial=pre.material.deepcopy()
	if not pre.plateMaterial: pre.plateMaterial=pre.cylMaterial.deepcopy()
	pre.material.id=0
	pre.cylMaterial.id=1
	pre.plateMaterial.id=2
	sideWallMat=pre.plateMaterial.deepcopy()
	sideWallMat.tanPhi=0.0
	sideWallMat.id=3

	
	# generate cylinder coordinates, or use those given by the user
	if pre.cylXzd:
		if pre.variant not in ('plain','customer2'): raise ValueError("Roro.cylXzd can be given as coordinates only with Roro.variant 'plain'/'customer2' (not '%s')."%pre.variant)
		cylXzd=pre.cylXzd
	else:
		cylXzd=[]
		dCyl=pre.cylDiameter
		xz0=(0,-dCyl/2) # first cylinder is right below the feed end at (0,0)
		if pre.variant=='customer1': xz0=(0,0)
		elif pre.variant=='customer2': xz0=(0,0)
		for i in range(0,max(pre.cylNum,len(pre.gaps)+1)):
			if pre.gaps: dist=i*dCyl+sum(pre.gaps[:i])
			else: dist=i*(dCyl+pre.gap) # distance from the first cylinder's center
			cylXzd.append(Vector3(xz0[0]+math.cos(pre.inclination)*dist,xz0[1]-math.sin(pre.inclination)*dist,dCyl))
	cylXMax=max([xzd[0] for xzd in cylXzd])
	cylZMin=min([xzd[1] for xzd in cylXzd])
	cylDMax=max([xzd[2] for xzd in cylXzd])
	print 'Cylinder coordinates and diameters (%d cylinders):'%len(cylXzd)
	pprint.pprint(cylXzd)

	rMin=pre.psd[0][0]/2.
	rMax=pre.psd[-1][0]/2.
	s.dt=pre.pWaveSafety*utils.spherePWaveDt(rMin,pre.material.density,pre.material.young)

	# particle masks
	wallMask=0b00110
	loneMask=0b00100 # particles with this mask don't interact with each other
	sphMask= 0b00011
	delMask= 0b00001 # particles which might be deleted by deleters
	s.dem.loneMask=loneMask
	
	###
	### conveyor feed
	###
	print 'Preparing packing for conveyor feed, be patient'
	cellLen=15*pre.psd[-1][0]
	cc,rr=makeBandFeedPack(dim=(cellLen,pre.cylLenSim,pre.conveyorHt),excessWd=(30*rMax,15*rMax),psd=pre.psd,mat=pre.material,gravity=(0,0,-pre.gravity),porosity=.7,damping=.3,memoizeDir=pre.feedCacheDir)
	vol=sum([4/3.*math.pi*r**3 for r in rr])
	conveyorVel=(pre.massFlowRate*pre.cylRelLen)/(pre.material.density*vol/cellLen)
	print 'Feed velocity %g m/s to match feed mass %g kg/m (volume=%g m³, len=%gm, ρ=%gkg/m³) and massFlowRate %g kg/s (%g kg/s over real width)'%(conveyorVel,pre.material.density*vol/cellLen,vol,cellLen,pre.material.density,pre.massFlowRate*pre.cylRelLen,pre.massFlowRate)

	facetHalfThick=4*rMin

	ymin,ymax=-pre.cylLenSim/2.,pre.cylLenSim/2.
	if pre.variant=='plain':
		# define simulation domain
		zmin,zmax=cylZMin-2*cylDMax,max(4*cylDMax,4*pre.conveyorHt)
		xmin,xmax=-3*cylDMax,cylXzd[-1][0]+3*cylDMax
		factoryNode=Node(pos=(xmin,0,0))

		de.par.append(ySpannedFacets((0,xmin),(ymin,ymax),(0,0),mat=pre.plateMaterial,mask=wallMask,fakeVel=(conveyorVel,0,0),halfThick=facetHalfThick))
	elif pre.variant=='customer1':
		# F                E is cylinder top; D is feed conveyor start, |D-E|=10cm
		# ____ E           cylinder radius 4cm, centered at D=C-(0,4cm)
		#   (_)  C         B-C vertical, |B-C|=27cm; C is at the leftmost point of the cylinder
		# D   |  
		#     |            |A-B|=28cm
		#   B ^-_          A-B in inclined by 19° more than the screen
		#        ^-_  A    cylinder below touched at point A
		#          ( )      centered at (0,0)
		#
		A=cylXzd[0][2]*.5*Vector2(math.sin(pre.inclination),math.cos(pre.inclination))
		A+=(0,5e-3) # move 5mm above
		abAngle=pre.inclination+math.radians(19)
		abLen=0.28
		B=A+abLen*Vector2(-math.cos(abAngle),math.sin(abAngle))
		upCylRad=0.04
		C=B+Vector2(0,0.27)
		D=C+Vector2(-upCylRad,0)
		E=D+Vector2(0,upCylRad)
		F=E+Vector2(-.1,0)
		#for i in 'ABCDEF': print i,eval(i)
		yy=(ymin,ymax)
		kw=dict(mat=pre.plateMaterial,mask=wallMask,halfThick=facetHalfThick)
		de.par.append(ySpannedFacets((A[0],B[0]),yy,(A[1],B[1]),**kw)+ySpannedFacets((B[0],C[0]),yy,(B[1],C[1]),**kw)+ySpannedFacets((E[0],F[0]),yy,(E[1],F[1]),fakeVel=(conveyorVel,0,0),**kw))
		del kw['halfThick']
		feedCyl=utils.infCylinder((D[0],0,D[1]),radius=upCylRad,axis=1,glAB=yy,**kw)
		feedCyl.angVel=Vector3(0,conveyorVel/upCylRad,0)
		de.par.append(feedCyl)

		zmin,zmax=cylZMin-2*cylDMax,F[1]+3*pre.conveyorHt
		xmin,xmax=F[0],cylXzd[-1][0]+3*cylDMax
		factoryNode=Node(pos=(F[0]+rMax,0,F[1]))
		
		if not pre.buckets: pre.buckets=[4,5,5,5]

	elif pre.variant=='customer2':
		#               
		# A        ___  B    B tangent of AB atop big cyl, A feed start
		#  __----^^ (+)  C   big cyl centerl C=(-.15,-.3)
		#            \   D   under big cyl
      #             \
		#              \ E   above first cyl
		#             (+)   (0,0) first cylinder
		bigCylR=.18
		angleAB=math.radians(8)
		E=Vector2(0,0)+Vector2(0,.5*cylXzd[0][2])
		C=Vector2(0,0)+Vector2(-.15,+.3)
		D=C+Vector2(0,-bigCylR)
		B=C+bigCylR*Vector2(-math.sin(angleAB),math.cos(angleAB))
		A=B+Vector2(-.4*bigCylR,-.4*bigCylR*math.tan(angleAB))

		yy=(ymin,ymax)
		kw=dict(mat=pre.plateMaterial,mask=wallMask,halfThick=facetHalfThick)
		de.par.append(ySpannedFacets((E[0],D[0]),yy,(E[1],D[1]),**kw)+ySpannedFacets((B[0],A[0]),yy,(B[1],A[1]),fakeVel=(math.sin(angleAB)*conveyorVel,0,math.cos(angleAB)*conveyorVel),**kw))
		del kw['halfThick']
		feedCyl=utils.infCylinder((C[0],0,C[1]),radius=bigCylR,axis=1,glAB=yy,**kw)
		feedCyl.angVel=Vector3(0,conveyorVel/bigCylR,0)
		de.par.append(feedCyl)
		zmin,zmax=cylZMin-2*cylDMax,B[1]+3*pre.conveyorHt
		xmin,xmax=min(A[0]-pre.conveyorHt*math.sin(angleAB)-rMax,B[0]-bigCylR),cylXzd[-1][0]+3*cylDMax
		factoryNode=Node(pos=(A[0],0,A[1]),ori=Quaternion((0,1,0),-angleAB))

		if not pre.buckets: pre.buckets=[len(cylXzd)]

	else: assert False

	factStep=pre.factStepPeriod
	factory=ConveyorFactory(
		stepPeriod=factStep,
		material=pre.material,
		centers=cc,radii=rr,
		cellLen=cellLen,
		barrierColor=.3,
		color=0,
		glColor=.5,
		#color=.4, # random colors
		node=factoryNode,
		mask=sphMask,
		vel=conveyorVel,
		label='factory',
		maxMass=-1, # not limited, until steady state is reached
		currRateSmooth=pre.rateSmooth,
	)

	###
	### walls and cylinders
	###		
	de.par.append([
		utils.wall(ymin,axis=1,sense= 1,visible=False,glAB=((zmin,xmin),(zmax,xmax)),mat=sideWallMat,mask=wallMask),
		utils.wall(ymax,axis=1,sense=-1,visible=False,glAB=((zmin,xmin),(zmax,xmax)),mat=sideWallMat,mask=wallMask),
		utils.wall(xmin,axis=0,sense= 1,visible=False,glAB=((ymin,zmin),(ymax,zmax)),mat=sideWallMat,mask=wallMask),
		utils.wall(xmax-4*rMax,axis=0,sense=-1,visible=False,glAB=((ymin,zmin),(ymax,zmax)),mat=sideWallMat,mask=wallMask),
		utils.wall(zmin+4*rMax,axis=2,sense= 1,visible=False,glAB=((xmin,ymin),(xmax,ymax)),mat=sideWallMat,mask=wallMask),
	])
	for i,xzd in enumerate(cylXzd):
		x,z,d=xzd
		c=utils.infCylinder((x,0,z),radius=d/2.,axis=1,glAB=(ymin,ymax),mat=pre.cylMaterial,mask=wallMask)
		c.angVel=(0,pre.angVel,0)
		qv,qh=pre.quivVPeriod,pre.quivHPeriod
		if pre.quivAmp.norm()>0:
			c.impose=AlignedHarmonicOscillations(
				amps=(pre.quivAmp[0]*d/2.,nan,pre.quivAmp[1]*d/2.),
				freqs=(
					1./((qh[0]+(i%int(qh[2]))*(qh[1]-qh[0])/int(qh[2]))*s.dt),
					nan,
					1./((qv[0]+(i%int(qv[2]))*(qv[1]-qv[0])/int(qv[2]))*s.dt)
				)
			)
		de.par.append(c)

	###
	### PLASTIC THINNING
	###
	if pre.thinningCoeffs[0]>0:
		thinningFactor,rMinFrac=pre.thinningCoeffs
		recoverRadius=True
	else:
		thinningFactor,rMinFrac=-1,1.
		recoverRadius=False

	###
	### buckets
	###
	bucketDeleters=[]
	barriersAt=[0] # barriers between buckets, indices are cylinder numbers
	if not pre.buckets: pre.buckets=[1]*(len(cylXzd)-1) # one bucket for each gap
	# non-positive indices count from the end
	else:
		bb=[]
		for b in pre.buckets: bb.append(b if b>0 else len(cylXzd)+b-bb[-1])
		pre.buckets=bb
	if sum(pre.buckets)<(len(cylXzd)-1): # no negative index, going till the end automatically
		print 'Buckets not reaching to the end of the screen, adding extra bucket'
		pre.buckets=pre.buckets+[len(cylXzd)-1-sum(pre.buckets)]
	bucketStart=0 # cylinder index where the current bucket starts
	for i,bucketWidth in enumerate(pre.buckets):
		if bucketStart>=(len(cylXzd)-1):
			print 'Buckets beyond cylinders specified, some will be discarded'
			break
		x,z,d=cylXzd[i]
		bucketEnd=bucketStart+bucketWidth # cylinder index where the current bucket ends
		if bucketEnd>=len(cylXzd):
			print 'Bucket width %d beyond cylinders, will be narrowed to %d.'%(bucketWidth,len(cylXzd)-bucketStart-1)
			bucketEnd=len(cylXzd)-1
		barriersAt.append(bucketEnd)
		xzd0,xzd1=cylXzd[bucketStart],cylXzd[bucketEnd]
		# initially don't save deleted particles
		bucketDeleters.append(BoxDeleter(stepPeriod=factStep,inside=True,box=((xzd0[0],ymin,zmin),(xzd1[0],ymax,min(xzd0[1]-xzd0[2]/2.,xzd1[1]-xzd1[2]/2.))),glColor=.5+(i*.5/len(pre.buckets)),save=False,mask=delMask,currRateSmooth=pre.rateSmooth,recoverRadius=recoverRadius,label='bucket[%d]'%i))
		bucketStart=bucketEnd
	# bucket barriers
	for cylI in barriersAt:
		x,z,d=cylXzd[cylI]
		de.par.append(ySpannedFacets((x,x),(ymin,ymax),(zmin,z-d/2.-facetHalfThick),shift=False,mat=pre.cylMaterial,mask=wallMask,visible=False,halfThick=facetHalfThick))

	###
	### engines
	###
	s.dem.gravity=(0,0,-pre.gravity)
	s.engines=utils.defaultEngines(damping=0.,verletDist=.05*rMin,
			cp2=Cp2_PelletMat_PelletPhys(),
			law=Law2_L6Geom_PelletPhys_Pellet(plastSplit=True,thinningFactor=thinningFactor,rMinFrac=rMinFrac)
		)+bucketDeleters+[
		# this one should not collect any particles at all
		BoxDeleter(stepPeriod=factStep,box=((xmin,ymin,zmin),(xmax,ymax,zmax)),glColor=.9,save=False,mask=delMask,label='outOfDomain'),
		# what falls inside
		BoxDeleter(stepPeriod=factStep,inside=True,box=((cylXzd[-1][0]+cylXzd[-1][2]/2.,ymin,zmin),(xmax,ymax,zmax)),glColor=.9,save=True,mask=delMask,currRateSmooth=pre.rateSmooth,recoverRadius=recoverRadius,label='fallOver'),
		# generator
		factory,
		PyRunner(factStep,'import woo.pre.roro; woo.pre.roro.savePlotData(S)'),
		PyRunner(factStep,'import woo.pre.roro; woo.pre.roro.watchProgress(S)'),
	]+(
		[Tracer(stepPeriod=20,num=100,compress=2,compSkip=4,dead=True,scalar=Tracer.scalarRadius)] if 'opengl' in woo.config.features else []
	)+(
		[] if (not pre.vtkPrefix or pre.vtkFreq<=0) else [VtkExport(out=pre.vtkPrefix,stepPeriod=int(pre.vtkFreq*pre.factStepPeriod),what=VtkExport.all,subdiv=16)]
	)+(
		[] if pre.backupSaveTime<=0 else [PyRunner(realPeriod=pre.backupSaveTime,stepPeriod=-1,command='S.save(S.pre.saveFmt.format(stage="backup-%06d"%(S.step),S=S,**(dict(S.tags))))')]
	)

	# improtant: save the preprocessor here!
	s.pre=pre.deepcopy() # avoids bug http://gpu.doxos.eu/trac/ticket/81, which might get triggered here
	de.collectNodes()

	if pre.mass:
		import woo
		for a in woo.bucket: a.save=True
		woo.factory.save=True
		woo.factory.maxMass=pre.mass*pre.cylRelLen

	# when running with gui, set initial view setup
	# the import fails if headless
	try:
		import woo.gl
		# set other display options and save them (static attributes)
		woo.gl.Gl1_DemField.colorRanges[woo.gl.Gl1_DemField.colorVel].range=(0,.5)
		s.any=[
			woo.gl.Renderer(iniUp=(0,0,1),iniViewDir=(0,1,0)),
			#woo.gl.Gl1_DemField(glyph=woo.gl.Gl1_DemField.glyphVel),
			woo.gl.Gl1_DemField(colorBy=woo.gl.Gl1_DemField.colorVel),
			woo.gl.Gl1_InfCylinder(wire=True),
			woo.gl.Gl1_Wall(div=1),
		]
	except ImportError: pass

	## Remove later, not neede for real simulations
	# s.trackEnergy=True

	print 'Generated Rollenrost.'
	out=pre.saveFmt.format(stage='init',S=s,**(dict(s.tags)))
	s.save(out)
	print 'Saved initial simulation also to ',out

	return s


def makeBandFeedPack(dim,psd,mat,gravity,excessWd=None,damping=.3,porosity=.5,goal=.15,dontBlock=False,memoizeDir=None,botLine=None,leftLine=None,rightLine=None):
	'''Create dense packing periodic in the +y direction, suitable for use with ConveyorFactory.'''
	print 'woo.pre.roro.makeBandFeedPack(dim=%s,psd=%s,mat=%s,gravity=%s,excessWd=%s,damping=%s,dontBlock=True,botLine=%s,leftLine=%s,rightLine=%s)'%(repr(dim),repr(psd),mat.dumps(format='expr',width=-1,noMagic=True),repr(gravity),repr(excessWd),repr(damping),repr(botLine),repr(leftLine),repr(rightLine))
	dim=list(dim) # make modifiable in case of excess width
	retWd=dim[1]
	repeatCell=[0]
	# too wide band is created by repeating narrower one
	if excessWd:
		if dim[1]>excessWd[0]:
			print 'makeBandFeedPack: excess with %g>%g, using %g with packing repeated'%(dim[1],excessWd[0],excessWd[1])
			retWd=dim[1]
			dim[1]=excessWd[1]
			nCopy=int(retWd/dim[1])+1
			repeatCell=range(-nCopy,nCopy+1)
	cellSize=(dim[0],dim[1],(1+2*porosity)*dim[2])
	print 'cell size',cellSize,'target height',dim[2]
	if memoizeDir and not dontBlock:
		params=str(dim)+str(cellSize)+str(psd)+str(goal)+str(damping)+mat.dumps(format='expr')+str(gravity)+str(porosity)+str(botLine)+str(leftLine)+str(rightLine)
		import hashlib
		paramHash=hashlib.sha1(params).hexdigest()
		memoizeFile=memoizeDir+'/'+paramHash+'.bandfeed'
		print 'Memoize file is ',memoizeFile
		if os.path.exists(memoizeDir+'/'+paramHash+'.bandfeed'):
			print 'Returning memoized result'
			sp=pack.SpherePack()
			sp.load(memoizeFile)
			return zip(*sp)
	S=Scene(fields=[DemField(gravity=gravity)])
	S.periodic=True
	S.cell.setBox(cellSize)
	factoryBottom=.3*cellSize[2] if not botLine else max([b[1] for b in botLine]) # point above which are particles generated
	factoryLeft=0 if not leftLine else max([l[0] for l in leftLine])
	#print 'factoryLeft =',factoryLeft,'leftLine =',leftLine,'cellSize =',cellSize
	factoryRight=cellSize[1] if not rightLine else min([r[0] for r in rightLine])
	if not leftLine: leftLine=[Vector2(0,cellSize[2])]
	if not rightLine:rightLine=[Vector2(cellSize[1],cellSize[2])]
	if not botLine:  botLine=[Vector2(0,0),Vector2(cellSize[1],0)]
	boundary2d=leftLine+botLine+rightLine
	p=pack.sweptPolylines2gtsSurface([utils.tesselatePolyline([Vector3(x,yz[0],yz[1]) for yz in boundary2d],maxDist=min(cellSize[0]/4.,cellSize[1]/4.,cellSize[2])/4.) for x in numpy.linspace(0,cellSize[0],num=4)])
	S.dem.par.append(pack.gtsSurface2Facets(p,mask=0b011))
	S.dem.loneMask=0b010

	massToDo=porosity*mat.density*dim[0]*dim[1]*dim[2]
	print 'Will generate %g mass'%massToDo

	## FIXME: decrease friction angle to help stabilization
	mat0,mat=mat,mat.deepcopy()
	mat.tanPhi=min(.2,mat0.tanPhi)


	S.engines=utils.defaultEngines(damping=damping)+[
		BoxFactory(
			box=((.01*cellSize[0],factoryLeft,factoryBottom),(cellSize[0],factoryRight,cellSize[2])),
			stepPeriod=200,
			maxMass=massToDo,
			massFlowRate=0,
			maxAttempts=20,
			generator=PsdSphereGenerator(psdPts=psd,discrete=False,mass=True),
			materials=[mat],
			shooter=AlignedMinMaxShooter(dir=(0,0,-1),vRange=(0,0)),
			mask=1,
			label='makeBandFeedFactory',
			#periSpanMask=1, # x is periodic
		),
		#PyRunner(200,'plot.addData(uf=utils.unbalancedForce(),i=O.scene.step)'),
		PyRunner(300,'import woo\nprint "%g/%g mass, %d particles, unbalanced %g/'+str(goal)+'"%(woo.makeBandFeedFactory.mass,woo.makeBandFeedFactory.maxMass,len(S.dem.par),woo.utils.unbalancedForce(S))'),
		PyRunner(300,'import woo\nif woo.makeBandFeedFactory.mass>=woo.makeBandFeedFactory.maxMass: S.engines[0].damping=1.5*%g'%damping),
		PyRunner(200,'import woo\nif woo.utils.unbalancedForce(S)<'+str(goal)+' and woo.makeBandFeedFactory.dead: S.stop()'),
	]
	S.dt=.7*utils.spherePWaveDt(psd[0][0],mat.density,mat.young)
	print 'Factory box is',woo.makeBandFeedFactory.box
	if dontBlock: return S
	else: S.run()
	S.wait()
	cc,rr=[],[]
	for p in S.dem.par:
		if not type(p.shape)==Sphere: continue
		for rep in repeatCell:
			c,r=S.cell.canonicalizePt(p.pos)+dim[1]*(rep-.5)*Vector3.UnitY,p.shape.radius
			if abs(c[1])+r>.5*retWd or c[2]+r>dim[2]: continue
			cc.append(Vector3(c[0],c[1],c[2])); rr.append(r)
	if memoizeDir:
		sp=pack.SpherePack()
		for c,r in zip(cc,rr): sp.add(c,r)
		print 'Saving to',memoizeFile
		sp.save(memoizeFile)
	return cc,rr


def watchProgress(S):
	'''initially, only the fallOver deleter saves particles; once particles arrive,
	it means we have reached some steady state; at that point, all objects (deleters,
	factory, ... are clear()ed so that PSD's and such correspond to the steady
	state only'''
	import woo
	pre=S.pre

	def saveWithPlotData(S):
		import woo.plot, pickle
		out=S.pre.saveFmt.format(stage='done',S=S,**(dict(S.tags)))
		if S.lastSave!=out:
			S.save(out)
			print 'Saved to',out

	## wait for steady state, then simulate pre.time time of steady state
	if pre.time>0:
		assert pre.mass<=0
		# not yet saving what falls through, i.e. not in stabilized regime yet
		if woo.bucket[0].save==False:
			# first particles have just fallen over
			# start saving buckets and reset our counters here
			#if woo.fallOver.num>pre.steadyOver:
			influx,efflux=woo.factory.currRate,(woo.fallOver.currRate+woo.outOfDomain.currRate+sum([a.currRate for a in woo.bucket]))
			if efflux>pre.steadyFlowFrac*influx:
				#print efflux,'>',pre.steadyFlowFrac,'*',influx
				woo.fallOver.clear()
				woo.factory.clear() ## FIXME
				woo.factory.maxMass=pre.time*pre.cylRelLen*pre.massFlowRate # required mass scaled to simulated part
				for ap in woo.bucket:
					ap.clear() # to clear overall mass, which gets counted even with save=False
					ap.save=True
				print 'Stabilized regime reached (influx %g, efflux %g) at step %d (t=%gs), counters engaged.'%(influx,efflux,S.step,S.time)
				out=S.pre.saveFmt.format(stage='steady',S=S,**(dict(S.tags)))
				S.save(out)
				print 'Saved to',out
		# already in the stable regime, end simulation at some point
		else:
			# factory has finished generating particles
			if woo.factory.mass>woo.factory.maxMass:
				print 'All mass generated at step %d (t=%gs, mass %g/%g), ending.'%(S.step,S.time,woo.factory.mass,woo.factory.maxMass)
				try:
					saveWithPlotData(S)
					writeReport(S)
				except:
					import traceback
					traceback.print_exc()
					print 'Error during post-processing.'
				print 'Simulation finished.'
				S.stop()
	elif pre.mass>0:
		assert pre.time<=0
		## after the mass is reached, continue for some time (say 20% of the simulation up to now), then finish
		if woo.factory.mass>=woo.factory.maxMass:
			delRate=sum([a.currRate for a in woo.bucket+[woo.fallOver]])
			if delRate<pre.residueFlowFrac*pre.cylRelLen*pre.massFlowRate: # feed flow rate scaled to simulated width
				print 'Delete rate dropped under %g×%g kg/s, ending simulation.'%(pre.residueFlowFrac,pre.massFlowRate)
				try:
					saveWithPlotData(S)
					writeReport(S)
				except:
					import traceback
					traceback.print_exc()
					print 'Error during post-processing.'
				print 'Simulation finished.'
				S.stop()
	else: assert False

def savePlotData(S):
	import woo
	#if woo.bucket[0].save==False: return # not in the steady state yet
	import woo.plot
	# save unscaled data here!
	bucketRate=sum([a.currRate for a in woo.bucket])
	overRate=woo.fallOver.currRate
	lostRate=woo.outOfDomain.currRate
	# keep in sync in report-generating routine (looks up data based on this!)
	eff=[(u'%g×gap=%g'%(gapFrac,gapFrac*S.pre.gap)) for gapFrac in S.pre.efficiencyGapFrac]
	otherData={}
	if woo.fallOver.num>100:
		for i,gapFrac in enumerate(S.pre.efficiencyGapFrac):
			dd=S.pre.gap*gapFrac
			mUnderProduct=sum([dm[1] for dm in zip(*woo.fallOver.diamMass()) if dm[0]<dd])
			mUnderBucket=sum([sum([dm[1] for dm in zip(*buck.diamMass()) if dm[0]<dd]) for buck in woo.bucket])
			if mUnderBucket+mUnderProduct!=0: # avoid zero division
				otherData[eff[i]]=mUnderBucket/(mUnderBucket+mUnderProduct)
	if S.trackEnergy: otherData.update(ERelErr=S.energy.relErr() if S.step>200 else float('nan'),**S.energy)
	S.plot.addData(i=S.step,t=S.time,genRate=woo.factory.currRate,bucketRate=bucketRate,overRate=overRate,lostRate=lostRate,delRate=bucketRate+overRate+lostRate,numPar=len(S.dem.par),genMass=woo.factory.mass,**otherData)
	if not S.plot.plots:
		S.plot.plots={'t':('genRate','bucketRate','lostRate','overRate','delRate',None,('numPar','g--')),' t':eff}
		if S.trackEnergy: S.plot.plots.update({'  t':(S.energy,None,('ERelErr','g--'))})

def splitPsd(xx0,yy0,splitX):
	'''Split input *psd0* (given by *xx0* and *yy0*) at diameter (x-axis) specified by *splitX*; two PSDs are returned, one grows from splitX and has maximum value for all points x>=splitX; the second PSD is zero for all values <=splitX, then grows to the maximum value proportionally. The maximum value is the last point of psd0, thus both normalized and non-normalized input can be given. If splitX falls in the middle of *psd0* intervals, it is interpolated.'''
	maxY=float(yy0[-1])
	assert(len(xx0)==len(yy0))
	import bisect
	ix=bisect.bisect(xx0,splitX)
	#print 'split index %d/%d'%(ix,len(xx0))
	if ix==0: return (xx0,[0.]*len(xx0)),(xx0,yy0)
	if ix==len(xx0): return (xx0,yy0),(xx0,[maxY]*len(xx0))
	splitY=yy0[ix-1]+(yy0[ix]-yy0[ix-1])*(splitX-xx0[ix-1])/(xx0[ix]-xx0[ix-1])
	smallTrsf,bigTrsf=lambda y: 0.+(y-0)*1./(splitY/maxY),lambda y: 0.+(y-splitY)*1./(1-splitY/maxY)
	#print 'splitY/maxY = %g/%g'%(splitY,maxY)
	xx1,yy1,xx2,yy2=[],[],[],[]
	for i in range(0,ix):
		xx1.append(xx0[i]); yy1.append(smallTrsf(yy0[i]))
		xx2.append(xx0[i]); yy2.append(0.)
	xx1.append(splitX); xx2.append(splitX);
	yy1.append(maxY); yy2.append(0.)
	for i in range(ix,len(xx0)):
		xx1.append(xx0[i]); yy1.append(1.)
		xx2.append(xx0[i]); yy2.append(bigTrsf(yy0[i]))
	return (xx1,yy1),(xx2,yy2)

def svgFileFragment(filename):
	import codecs
	data=codecs.open(filename,encoding='utf-8').read()
	return data[data.find('<svg '):]

def psdFeedBucketFalloverTable(inPsd,feedDM,bucketDM,overDM,splitD):
	import collections, numpy
	TabLine=collections.namedtuple('TabLine','dMin dMax dAvg inFrac feedFrac feedSmallFrac feedBigFrac overFrac')
	feedD,feedM=feedDM
	dScale=1e3 # m → mm
	# must convert to list to get slices right in the next line
	edges=list(inPsd[0]) # those will be displayed in the table
	# enlarge a bit so that marginal particles, if any, fit in comfortably; used for histogram computation
	bins=numpy.array([.99*edges[0]]+edges[1:-1]+[1.01*edges[-1]]) 
	edges=numpy.array(edges) # convert back
	# cumulative; otherwise use numpy.diff
	inHist=numpy.diff(inPsd[1]) # non-cumulative
	feedHist,b=numpy.histogram(feedD,weights=feedM,bins=bins,density=True)
	feedHist/=sum(feedHist)
	feedSmallHist,b=numpy.histogram(feedD[feedD<splitD],weights=feedM[feedD<splitD],bins=bins,density=True)
	feedSmallHist/=sum(feedSmallHist)
	feedBigHist,b=numpy.histogram(feedD[feedD>=splitD],weights=feedM[feedD>=splitD],bins=bins,density=True)
	feedBigHist/=sum(feedBigHist)
	overHist,b=numpy.histogram(overDM[0],weights=overDM[1],bins=bins,density=True)
	overHist/=sum(overHist)
	tab=[]
	for i in range(0,len(inHist)):
		tab.append(TabLine(dMin=edges[i],dMax=edges[i+1],dAvg=.5*(edges[i]+edges[i+1]),inFrac=inHist[i],feedFrac=feedHist[i],feedSmallFrac=feedSmallHist[i],feedBigFrac=feedBigHist[i],overFrac=overHist[i]))
	from genshi.builder import tag as t
	return unicode(t.table(
		t.tr(
			t.th('Diameter',t.br,'[mm]'),t.th('Average',t.br,'[mm]'),t.th('user input',t.br,'[mass %]',colspan=2),t.th('feed',t.br,'[mass %]',colspan=2),t.th('feed < %g mm'%(dScale*splitD),t.br,'[mass %]',colspan=2),t.th('feed > %g mm'%(dScale*splitD),t.br,'[mass %]',colspan=2),t.th('fall over',t.br,'[mass %]',colspan=2),align='center'
		),
		*tuple([t.tr(
			t.td('%g-%g'%(dScale*tt.dMin,dScale*tt.dMax),align='left'),t.td('%g'%(dScale*tt.dAvg),align='right'),
			t.td('%.4g'%(1e2*tt.inFrac)),t.td('%.4g'%(1e2*sum([ttt.inFrac for ttt in tab[:i+1]]))),
			t.td('%.4g'%(1e2*tt.feedFrac)),t.td('%.4g'%(1e2*sum([ttt.feedFrac for ttt in tab[:i+1]]))),
			t.td('%.4g'%(1e2*tt.feedSmallFrac)),t.td('%.4g'%(1e2*sum([ttt.feedSmallFrac for ttt in tab[:i+1]]))),
			t.td('%.4g'%(1e2*tt.feedBigFrac)),t.td('%.4g'%(1e2*sum([ttt.feedBigFrac for ttt in tab[:i+1]]))),
			t.td('%.4g'%(1e2*tt.overFrac)),t.td('%.4g'%(1e2*sum([ttt.overFrac for ttt in tab[:i+1]]))),
			align='right'
		) for i,tt in enumerate(tab)])
		,cellpadding='2px',frame='box',rules='all'
	).generate().render('xhtml'))

def bucketPsdTable(S,massName,massScale,massUnit,massBasedPsd=True):
	print 'bucketPsdTable',S.pre.psd
	psdSplits=[df[0] for df in S.pre.psd]
	buckMasses=[]
	for buck in woo.bucket:
		mm=[]
		for i in range(len(psdSplits)-1):
			dmdm=zip(*buck.diamMass())
			mm.append(sum([(dm[1] if massBasedPsd else 1.) for dm in dmdm if (dm[0]>=psdSplits[i] and dm[0]<psdSplits[i+1])]))
		buckMasses.append(mm)
		print buck.mass,sum(mm)
	from genshi.builder import tag as t
	tab=t.table(
		t.tr(t.th('diameter',t.br,'[mm]'),*tuple([t.th('bucket %d'%i,t.br,'[%s %%]'%massName,colspan=2) for i in range(len(woo.bucket))])),
		cellpadding='2px',frame='box',rules='all'
	)
	dScale=1e3 # m to mm
	for i in range(len(psdSplits)-1):
		tr=t.tr(t.td('%g-%g'%(dScale*psdSplits[i],dScale*psdSplits[i+1])))
		for bm in buckMasses:
			bMass=sum(bm)
			try:
				tr.append(t.td('%.4g'%(100*bm[i]/bMass),align='right'))
				tr.append(t.td('%.4g'%(100*sum(bm[:i+1])/bMass),align='right'))
			except ZeroDivisionError:
				tr.append(t.td('-',align='right')); tr.append(t.td('-',align='right'))
		tab.append(tr)
	bucketsTotal=sum([sum(bm) for bm in buckMasses])*massScale
	feedTotal=(woo.factory.mass if massBasedPsd else woo.factory.num)*massScale
	tab.append(t.tr(t.th('%s [%s]'%(massName,massUnit),rowspan=2),*tuple([t.th('%g'%(sum(bm)*massScale),colspan=2) for bm in buckMasses])))
	tab.append(t.tr(t.th('%g / %g = %.4g%%'%(bucketsTotal,feedTotal,bucketsTotal*100./feedTotal),colspan=2*len(buckMasses))))
	return unicode(tab.generate().render('xhtml'))


def efficiencyTableFigure(S,pre):
	# split points
	diams=[p[0] for p in pre.psd]
	if pre.gap not in diams: diams.append(pre.gap)
	diams.sort()
	diams=diams[1:-1] # smallest and largest are meaningless (would have 0%/100% everywhere)
	import numpy
	# each line is for one bucket
	# each column is for one fraction
	data=numpy.zeros(shape=(len(woo.bucket),len(diams)))
	for apNum,bucket in enumerate(woo.bucket):
		xMin,xMax=bucket.box.min[0],bucket.box.max[0]
		massTot=0.
		for p in S.dem.par:
			# only spheres above the bucket count
			if not isinstance(p.shape,woo.dem.Sphere) or p.pos[0]<xMin or p.pos[1]>xMax: continue
			massTot+=p.mass
			for i,d in enumerate(diams):
				if 2*p.shape.radius>d: continue
				data[apNum][i]+=p.mass
		data[apNum]/=massTot
	from genshi.builder import tag as t
	table=unicode(t.table(
		[t.tr([t.th()]+[t.th('Bucket %d'%(apNum+1)) for apNum in range(len(woo.bucket))])]+
		[t.tr([t.th('< %.4g mm'%(1e3*diams[dNum]))]+[t.td('%.1f %%'%(1e2*data[apNum][dNum]),align='right') for apNum in range(len(woo.bucket))]) for dNum in range(len(diams))]
		,cellpadding='2px',frame='box',rules='all'
	).generate().render('xhtml'))
	import pylab
	fig=pylab.figure()
	for dNum,d in reversed(list(enumerate(diams))): # displayed from the bigger to smaller, to make legend aligned with lines
		pylab.plot(numpy.arange(len(woo.bucket))+1,data[:,dNum],marker='o',label='< %.4g mm'%(1e3*d))
	from matplotlib.ticker import FuncFormatter
	percent=FuncFormatter(lambda x,pos=0: '%g%%'%(100*x))
	pylab.gca().yaxis.set_major_formatter(percent)
	pylab.ylabel('Mass fraction')
	pylab.xlabel('Bucket number')
	pylab.ylim(ymin=0,ymax=1)
	l=pylab.legend()
	l.get_frame().set_alpha(.6)
	pylab.grid(True)
	return table,fig

def bucketEfficiencyExtra(name,buck,feed,dMin,dMax):
	## per-bucket efficiency relative to gap size
	mFeedFrac=1.*sum([dm[1] for dm in zip(*feed.diamMass()) if dm[0]>dMin and dm[0]<dMax])
	#print 'Fraction %g-%g in feed: %g kg'%(dMin*1e3,dMax*1e3,mFeedFrac)
	mBucketFrac=1.*sum([dm[1] for dm in zip(*buck.diamMass()) if dm[0]>dMin and dm[0]<dMax])
	#print 'Fraction %g-%g in %s: %g kg'%(dMin*1e3,dMax*1e3,name,mBucketFrac)
	print 'Efficiency for %g-%g (%s): %g%% (%gkg/%gkg)'%(dMin*1e3,dMax*1e3,name,100.*mBucketFrac/mFeedFrac,mBucketFrac,mFeedFrac)
	return '',[],{name:mBucketFrac/mFeedFrac}

def finesRemoval_productRecovery_extras(S,fineD,prodD):
	buckDm=sum([[dm for dm in zip(*buck.diamMass())] for buck in woo.bucket],[])
	# fine particles in buckets and in product
	buckFines,prodFines=sum([buck.massOfDiam(max=fineD) for buck in woo.bucket]),woo.fallOver.massOfDiam(max=fineD)
	# product-sized particles in buckets and in product
	buckProd,prodProd=sum([buck.massOfDiam(min=prodD) for buck in woo.bucket]),woo.fallOver.massOfDiam(min=prodD)
	return '',[],dict(finesRemovalEff=buckFines/(buckFines+prodFines),productRecoveryEff=prodProd/(buckProd+prodProd))


def xhtmlReportHead(S,headline):
	import time, platform
	xmlhead='''<?xml version="1.0" encoding="UTF-8"?>
	<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd"> 
	<html xmlns="http://www.w3.org/1999/xhtml" xmlns:svg="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
	'''
	# <meta http-equiv="content-type" content="text/html;charset=UTF-8" />
	html=(u'''<head><title>{headline}</title></head><body>
		<h1>{headline}</h1>
		<h2>General</h2>
		<table>
			<tr><td>title</td><td align="right">{title}</td></tr>
			<tr><td>id</td><td align="right">{id}</td></tr>
			<tr><td>operator</td><td align="right">{user}</td></tr>
			<tr><td>started</td><td align="right">{started}</td></tr>
			<tr><td>duration</td><td align="right">{duration:g} s</td></tr>
			<tr><td>number of cores used</td><td align="right">{nCores}</td></tr>
			<tr><td>average speed</td><td align="right">{stepsPerSec:g} steps/sec</td></tr>
			<tr><td>engine</td><td align="right">{engine}</td></tr>
			<tr><td>compiled with</td><td align="right">{compiledWith}</td></tr>
			<tr><td>platform</td><td align="right">{platform}</td></tr>
		</table>
		'''.format(headline=headline,title=(S.tags['title'] if S.tags['title'] else '<i>[none]</i>'),id=S.tags['id'],user=S.tags['user'].decode('utf-8'),started=time.ctime(time.time()-woo.master.realtime),duration=woo.master.realtime,nCores=woo.master.numThreads,stepsPerSec=S.step/woo.master.realtime,engine='wooDem '+woo.config.version+'/'+woo.config.revision+(' (debug)' if woo.config.debug else ''),compiledWith=','.join(woo.config.features),platform=platform.platform().replace('-',' '))
		+'<h2>Input data</h2>'+S.pre.dumps(format='html',fragment=True,showDoc=True)
	)
	return xmlhead+html


def writeReport(S):
	# generator parameters
	import woo
	import woo.pre
	pre=S.pre
	#pre=[a for a in woo.O.scene.any if type(a)==woo.pre.Roro][0]
	#print 'Parameters were:'
	#pre.dump(sys.stdout,noMagic=True,format='expr')

	import matplotlib.pyplot as pyplot
	try:
		import woo.qt
	except ImportError:
		# no display, use Agg backend
		pyplot.switch_backend('Agg')

	#import matplotlib
	#matplotlib.use('Agg')
	import pylab
	import os
	import numpy
	# http://www.mail-archive.com/matplotlib-users@lists.sourceforge.net/msg05474.html
	from matplotlib.ticker import FuncFormatter
	percent=FuncFormatter(lambda x,pos=0: '%g%%'%(100*x))
	milimeter=FuncFormatter(lambda x,pos=0: '%3g'%(1000*x))

	legendAlpha=.6

	# should this be scaled to t/year as well?
	# steady regime
	if pre.time>0: 
		massScale=(
			(1./pre.cylRelLen)*(1./pre.time) # in kg/sec
			*3600*1e-3 # in t/h
			#*3600*24*365/1000.  # in t/y
			#*1e-6 # in Mt/y
		)
		massUnit='t/h'
		massName='flow'
		massFormatter=FuncFormatter(lambda x,pos=0: '%3g\n$%3g/m$'%(x,x/pre.cylLenReal))
	else:
		# mass-based simulation (from beginning till the end)
		massScale=(1./pre.cylRelLen) # in kg
		massUnit='kg'
		massName='mass'
		massFormatter=None
	rateScale=(1./pre.cylRelLen)*3600*1e-3 # in t/h
	rateUnit='t/h'
	rateFormatter=FuncFormatter(lambda x,pos=0: '%3g\n$%3g/m$'%(x,x/pre.cylLenReal))

	def scaledFlowPsd(x,y,massFactor=1.): return numpy.array(x),massFactor*massScale*numpy.array(y)
	def unscaledPsd(x,y): return numpy.array(x),numpy.array(y)

	figs=[]
	fig=pylab.figure()

	inPsd=scaledFlowPsd([p[0] for p in pre.psd],[p[1]*(1./pre.psd[-1][1]) for p in pre.psd],massFactor=woo.factory.mass)
	inPsdUnscaled=unscaledPsd([p[0] for p in pre.psd],[p[1]*(1./pre.psd[-1][1]) for p in pre.psd])

	feedPsd=scaledFlowPsd(*woo.factory.psd())
	pylab.plot(*inPsd,label='user',marker='o')
	pylab.plot(*feedPsd,label='feed (%g %s)'%(woo.factory.mass*massScale,massUnit))
	if woo.fallOver.num>0:
		overPsd=scaledFlowPsd(*woo.fallOver.psd())
		pylab.plot(*overPsd,label='fall over (%.3g %s)'%(woo.fallOver.mass*massScale,massUnit))
	for i in range(0,len(woo.bucket)):
		try:
			bucketPsd=scaledFlowPsd(*woo.bucket[i].psd())
			pylab.plot(*bucketPsd,label='bucket %d (%.3g %s)'%(i,woo.bucket[i].mass*massScale,massUnit))
		except ValueError: pass
	pylab.axvline(x=pre.gap,linewidth=5,alpha=.3,ymin=0,ymax=1,color='g',label='gap')
	pylab.grid(True)
	leg=pylab.legend(loc='best')
	leg.get_frame().set_alpha(legendAlpha)
	pylab.gca().xaxis.set_major_formatter(milimeter)
	if massFormatter: pylab.gca().yaxis.set_major_formatter(massFormatter)
	pylab.xlabel('diameter [mm]')
	pylab.ylabel('cumulative %s [%s]'%(massName,massUnit))
	figs.append(('Cumulative %s'%massName,fig))

	#ax=pylab.subplot(222)
	fig=pylab.figure()
	dOver,mOver=scaledFlowPsd(*woo.fallOver.diamMass())
	dBuckets,mBuckets=numpy.array([]),numpy.array([])
	for a in woo.bucket:
		try:
			d,m=scaledFlowPsd(*a.diamMass())
			dBuckets=numpy.hstack([dBuckets,d]); mBuckets=numpy.hstack([mBuckets,m])
		except ValueError: pass
	if woo.fallOver.num>0:
		hh=pylab.hist([dOver,dBuckets],weights=[mOver,mBuckets],bins=20,histtype='barstacked',label=['fallOver','buckets'])
		flowBins=hh[1]
		feedD,feedM=scaledFlowPsd(*woo.factory.diamMass())
		pylab.plot(.5*(flowBins[1:]+flowBins[:-1]),numpy.histogram(feedD,weights=feedM,bins=flowBins)[0],label='feed',alpha=.3,linewidth=2,marker='o')
	pylab.axvline(x=pre.gap,linewidth=5,alpha=.3,ymin=0,ymax=1,color='g',label='gap')
	pylab.grid(True)
	pylab.gca().xaxis.set_major_formatter(milimeter)
	if massFormatter: pylab.gca().yaxis.set_major_formatter(massFormatter)
	pylab.xlabel('particle diameter [mm]')
	pylab.ylabel('%s [%s]'%(massName,massUnit))
	leg=pylab.legend(loc='best')
	leg.get_frame().set_alpha(legendAlpha)
	figs.append((massName.capitalize(),fig))

	##
	## PSD derivatives
	##
	fig=pylab.figure()
	for dd,mm,label in ((dOver,mOver,'oversize'),(dBuckets,mBuckets,'undersize')):
		from numpy import diff
		from matplotlib.mlab import movavg
		yPsd,xPsd=numpy.histogram(dd,weights=mm,bins=25)
		yPsd=1e-3*yPsd.cumsum()
		xMidPsd=.5*(xPsd[1:]+xPsd[:-1])
		pylab.plot(xMidPsd[1:-1],movavg(diff(yPsd)/diff(xMidPsd),2),label=label,linewidth=3)
		#print 'Derivative PSD '+label
		#print '\t',xMidPsd[1:-1]
		#print '\t',movavg(diff(yPsd)/diff(xMidPsd),2)
	pylab.grid(True)
	pylab.gca().xaxis.set_major_formatter(milimeter)
	pylab.axvline(x=pre.gap,linewidth=5,alpha=.3,ymin=0,ymax=1,color='g',label='gap')
	pylab.xlabel('particle diameter [mm]')
	pylab.ylabel('PSD derivative [%s/mm]'%(massUnit))
	leg=pylab.legend(loc='best')
	leg.get_frame().set_alpha(legendAlpha)
	figs.append(('Derivative PSD',fig))
	

	feedTab=psdFeedBucketFalloverTable(
		inPsd=inPsdUnscaled,
		feedDM=unscaledPsd(*woo.factory.diamMass()),
		bucketDM=(dBuckets,mBuckets),
		overDM=(dOver,mOver),
		splitD=pre.gap
	)

	# steady state was measured
	if pre.time>0:
		effTab,effFig=efficiencyTableFigure(S,pre)
		figs.append(('Sieving efficiency',effFig))
	# non-steady state was simulated
	if pre.mass: 
		effTab=None # must be assigned
		# must be kept in sync with labels in savePlotData
		effDataLabels=[(u'%g×gap=%g'%(gapFrac,gapFrac*S.pre.gap)) for gapFrac in S.pre.efficiencyGapFrac]
		fig=pylab.figure()
		pylab.grid(True)
		for eff in effDataLabels:
			pylab.plot(S.plot.data['t'],S.plot.data[eff],label=eff)
			pylab.xlabel('time [s]')
			pylab.ylabel('relative efficiency')
			pylab.gca().yaxis.set_major_formatter(percent)
		leg=pylab.legend(loc='best')
		leg.get_frame().set_alpha(legendAlpha)
		figs.append(('Sieving efficiency',fig))

	#ax=pylab.subplot(223)
	fig=pylab.figure()
	#print inPsdUnscaled
	#print inPsd
	pylab.plot(*inPsdUnscaled,marker='o',label='user')
	feedPsd=unscaledPsd(*woo.factory.psd(normalize=True))
	pylab.plot(*feedPsd,label=None)
	smallerPsd,biggerPsd=splitPsd(*inPsdUnscaled,splitX=pre.gap)
	#print smallerPsd
	#print biggerPsd
	pylab.plot(*smallerPsd,marker='v',label='user <')
	pylab.plot(*biggerPsd,marker='^',label='user >')

	splitD=pre.gap
	feedD,feedM=unscaledPsd(*woo.factory.diamMass())
	feedHist,feedBins=numpy.histogram(feedD,weights=feedM,bins=60)
	feedHist/=feedHist.sum()
	binMids=feedBins[1:] #.5*(feedBins[1:]+feedBins[:-1])
	feedSmallHist,b=numpy.histogram(feedD[feedD<splitD],weights=feedM[feedD<splitD],bins=feedBins,density=True)
	feedSmallHist/=feedSmallHist.sum()
	feedBigHist,b=numpy.histogram(feedD[feedD>=splitD],weights=feedM[feedD>=splitD],bins=feedBins,density=True)
	feedBigHist/=feedBigHist.sum()
	pylab.plot(binMids,feedHist.cumsum(),label=None)
	pylab.plot(binMids,feedSmallHist.cumsum(),label=None) #'feed <')
	pylab.plot(binMids,feedBigHist.cumsum(),label=None) #'feed >')
	feedD=feedPsd[0]

	pylab.axvline(x=pre.gap,linewidth=5,alpha=.3,ymin=0,ymax=1,color='g',label='gap')
	buckHist,buckBins=numpy.histogram(dBuckets,weights=mBuckets,bins=feedBins)
	buckHist/=buckHist.sum()
	overHist,overBins=numpy.histogram(dOver,weights=mOver,bins=feedBins)
	overHist/=overHist.sum()
	pylab.plot(binMids,buckHist.cumsum(),label='buckets',linewidth=3)
	pylab.plot(binMids,overHist.cumsum(),label='fall over',linewidth=3)
	pylab.ylim(ymin=-.05,ymax=1.05)

	#print 'smaller',smallerPsd
	#print 'bigger',biggerPsd
	pylab.grid(True)
	pylab.gca().xaxis.set_major_formatter(milimeter)
	pylab.xlabel('diameter [mm]')
	pylab.gca().yaxis.set_major_formatter(percent)
	pylab.ylabel('mass fraction')
	leg=pylab.legend(loc='best')
	leg.get_frame().set_alpha(legendAlpha)
	figs.append(('Efficiency',fig))


	# per-bucket PSD
	if 1:
		fig=pylab.figure()
		for i,buck in enumerate(woo.bucket):
			dm=buck.diamMass()
			h,bins=numpy.histogram(dm[0],weights=dm[1],bins=50)
			h/=h.sum()
			#h=pylab.hist(dm[0],bins=40,weights=dm[1],normed=True,histtype='step',label='bucket %d'%i,linewidth=2)
			pylab.plot(bins,[0]+list(h.cumsum()),label='bucket %d'%i,linewidth=2)
		#pylab.plot(binMids,h.cumsum(),label='bucket %d'%i,linewidth=2)
		pylab.ylim(ymin=-.05,ymax=1.05)
		pylab.grid(True)
		pylab.gca().xaxis.set_major_formatter(milimeter)
		pylab.xlabel('diameter [mm]')
		pylab.gca().yaxis.set_major_formatter(percent)
		pylab.ylabel('mass fraction')
		pylab.axvline(x=pre.gap,linewidth=5,alpha=.3,ymin=0,ymax=1,color='g',label='gap')
		leg=pylab.legend(loc='best')
		leg.get_frame().set_alpha(legendAlpha)
		figs.append(('Per-bucket PSD',fig))

	try:
		#ax=pylab.subplot(224)
		fig=pylab.figure()
		import woo.plot
		d=S.plot.data
		if S.pre.time>0:
			d['genRate'][-1]=d['genRate'][-2] # replace trailing 0 by the last-but-one value
		pylab.plot(d['t'],rateScale*numpy.array(d['genRate']),label='feed')
		pylab.plot(d['t'],rateScale*numpy.array(d['bucketRate']),label='buckets')
		pylab.plot(d['t'],rateScale*numpy.array(d['lostRate']),label='(lost)')
		pylab.plot(d['t'],rateScale*numpy.array(d['overRate']),label='fallOver')
		pylab.plot(d['t'],rateScale*numpy.array(d['delRate']),label='delete')
		pylab.ylim(ymin=0)
		#pylab.axvline(x=(S.time-pre.time),linewidth=5,alpha=.3,ymin=0,ymax=1,color='r',label='steady')
		if pre.time>0:	pylab.axvspan(S.time-pre.time,S.time,alpha=.2,facecolor='r',label='steady')
		leg=pylab.legend(loc='lower left')
		leg.get_frame().set_alpha(legendAlpha)
		pylab.grid(True)
		pylab.xlabel('time [s]')
		pylab.ylabel('mass rate [%s]'%rateUnit)
		pylab.gca().yaxis.set_major_formatter(rateFormatter)
		figs.append(('Regime',fig))
	except (KeyError,IndexError) as e:
		print 'No woo.plot plots done due to lack of data:',str(e)
		# after loading no data are recovered

	# custom report hooks
	extraHtml,extraFigs,extraResults='',[],{}
	for hook in pre.reportHooks:
		hh,ff,rr=eval(hook,globals(),dict(S=S))
		extraHtml+=hh
		extraFigs+=ff
		extraResults.update(rr)
	print 'Extra results from reportHooks:',extraResults

	repName=os.path.abspath(S.pre.reportFmt.format(S=S,**(dict(S.tags))))
	import re
	repExtra=re.sub('\.xhtml$','',repName)
	svgs=[]
	for ff in figs+extraFigs:
		if len(ff)==2: ff=(ff[0],ff[1],'svg')
		name,fig,extension=ff
		fname=repExtra+'.'+re.sub('[-()\[\] ]','_',name)+'.'+extension
		svgs.append((name,fname))
		fig.savefig(svgs[-1][-1])

	print 9,S.pre.psd
		
	import codecs
	html=xhtmlReportHead(S,'Report for Roller screen simulation')+(
		'<h2>Outputs</h2>'
		+'<h3>Feed</h3>'+feedTab
		+(('<h3>Sieving</h3>'+effTab) if effTab else '')
		+'<h3>Bucket PSD</h3>'
			+'<h4>Mass-based</h4>'+bucketPsdTable(S,massName=massName,massUnit=massUnit,massScale=massScale,massBasedPsd=True)
			+'<h4>Number-based</h4>'+bucketPsdTable(S,massName='number',massUnit='',massScale=massScale,massBasedPsd=False)
		+extraHtml
		+u'\n'.join([u'<h3>'+svg[0]+u'</h3>'+
			# svgFileFragment(svg[1])  # images inline
			'<img src="%s" alt="%s"/>'%(os.path.basename(svg[1]),svg[0]) # external images, in the same directory
		for svg in svgs])
		+'</body></html>'
	)

	print 10,S.pre.psd

	# to play with that afterwards
	woo.html=html
	rep=codecs.open(repName,'w','utf-8','replace')
	import os.path
	print 'Writing report to file://'+repName
	#rep.write(HTMLParser(StringIO.StringIO(html),'[filename]').parse().render('xhtml',doctype='xhtml').decode('utf-8'))
	s=html
	#s=s.replace(u'\xe2\x88\x92','-') # long minus
	#s=s.replace(u'\xc3\x97','x') # × multiplicator
	try:
		rep.write(s)
	except UnicodeDecodeError as e:
		print e.start,e.end
		print s[max(0,e.start-20):min(e.end+20,len(s))]
		raise e
	# close before the webbrowser reads the file
	rep.close()
		
	import woo.batch
	if not woo.batch.inBatch():
		import webbrowser
		webbrowser.open('file://'+os.path.abspath(repName),new=2) # new=2: new tab if possible

	# write results to the db
	woo.batch.writeResults(defaultDb='RoRo.sqlite',simulationName='RoRo',material=S.pre.material,report=repName,saveFile=os.path.abspath(S.lastSave),**extraResults)

	# save sphere's positions
	if 0:
		from woo import pack
		sp=pack.SpherePack()
		sp.fromSimulation(S)
		packName=S.tags['id.d']+'-spheres.csv'
		sp.save(packName)
		print 'Particles saved to',os.path.abspath(packName)

# test drive
if __name__=='__main__':
	import woo.pre
	import woo.qt
	import woo.log
	#woo.log.setLevel('PsdParticleGenerator',woo.log.TRACE)
	woo.master.scene=S=woo.pre.Roro()()
	S.timingEnabled=True
	S.saveTmp()
	woo.qt.View()
	S.run()
