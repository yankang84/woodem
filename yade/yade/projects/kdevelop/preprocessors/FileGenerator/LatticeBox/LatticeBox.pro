# File generated by kdevelop's qmake manager. 
# ------------------------------------------- 
# Subdir relative project main directory: ./preprocessors/FileGenerator/LatticeBox
# Target is a library:  

LIBS += -lParticleParameters \
        -lInteractionDescriptionSet \
        -lLatticeBeamParameters \
        -lLineSegment \
        -lLatticeNodeParameters \
        -lAABB \
        -lSphere \
        -lLatticeSetParameters \
        -lLatticeNodeParameters \
        -rdynamic 
INCLUDEPATH += $(YADEINCLUDEPATH) 
MOC_DIR = $(YADECOMPILATIONPATH) 
UI_DIR = $(YADECOMPILATIONPATH) 
OBJECTS_DIR = $(YADECOMPILATIONPATH) 
QMAKE_LIBDIR = ../../../plugins/Body/BodyPhysicalParameters/ParticleParameters/$(YADEDYNLIBPATH) \
               ../../../plugins/Body/InteractionDescription/InteractionDescriptionSet/$(YADEDYNLIBPATH) \
               ../../../plugins/Body/BodyPhysicalParameters/LatticeBeamParameters/$(YADEDYNLIBPATH) \
               ../../../plugins/Body/GeometricalModel/LineSegment/$(YADEDYNLIBPATH) \
               ../../../plugins/Body/BodyPhysicalParameters/LatticeNodeParameters/$(YADEDYNLIBPATH) \
               ../../../plugins/Body/BoundingVolume/AABB/$(YADEDYNLIBPATH) \
               ../../../plugins/Body/GeometricalModel/Sphere/$(YADEDYNLIBPATH) \
               $(YADEDYNLIBPATH) 
DESTDIR = $(YADEDYNLIBPATH) 
CONFIG += debug \
          warn_on \
          dll 
TEMPLATE = lib 
HEADERS += LatticeBox.hpp 
SOURCES += LatticeBox.cpp 
