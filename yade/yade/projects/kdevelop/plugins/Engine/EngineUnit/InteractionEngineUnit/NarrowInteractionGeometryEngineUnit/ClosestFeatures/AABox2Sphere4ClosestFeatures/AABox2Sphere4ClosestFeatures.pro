# File generated by kdevelop's qmake manager. 
# ------------------------------------------- 
# Subdir relative project main directory: ./plugins/Engine/EngineUnit/InteractionEngineUnit/NarrowInteractionGeometryEngineUnit/ClosestFeatures/AABox2Sphere4ClosestFeatures
# Target is a library:  

LIBS += -lBox \
        -lSphere \
        -lClosestFeatures \
        -lyade-lib-wm3-math \
        -lyade-lib-multimethods \
        -lInteractingSphere \
        -lInteractingBox \
        -rdynamic 
INCLUDEPATH = $(YADEINCLUDEPATH) 
MOC_DIR = $(YADECOMPILATIONPATH) 
UI_DIR = $(YADECOMPILATIONPATH) 
OBJECTS_DIR = $(YADECOMPILATIONPATH) 
QMAKE_LIBDIR = ../../../../../../../plugins/Data/Body/GeometricalModel/Box/$(YADEDYNLIBPATH) \
               ../../../../../../../plugins/Data/Body/GeometricalModel/Sphere/$(YADEDYNLIBPATH) \
               ../../../../../../../plugins/Data/Interaction/NarrowInteractionGeometry/ClosestFeatures/$(YADEDYNLIBPATH) \
               ../../../../../../../libraries/yade-lib-wm3-math/$(YADEDYNLIBPATH) \
               ../../../../../../../libraries/yade-lib-multimethods/$(YADEDYNLIBPATH) \
               ../../../../../../../plugins/Data/Body/InteractingGeometry/InteractingSphere/$(YADEDYNLIBPATH) \
               ../../../../../../../plugins/Data/Body/InteractingGeometry/InteractingBox/$(YADEDYNLIBPATH) \
               $(YADEDYNLIBPATH) 
QMAKE_CXXFLAGS_RELEASE += -lpthread \
                          -pthread 
QMAKE_CXXFLAGS_DEBUG += -lpthread \
                        -pthread 
DESTDIR = $(YADEDYNLIBPATH) 
CONFIG += debug \
          warn_on \
          dll 
TEMPLATE = lib 
HEADERS += AABox2Sphere4ClosestFeatures.hpp 
SOURCES += AABox2Sphere4ClosestFeatures.cpp 
