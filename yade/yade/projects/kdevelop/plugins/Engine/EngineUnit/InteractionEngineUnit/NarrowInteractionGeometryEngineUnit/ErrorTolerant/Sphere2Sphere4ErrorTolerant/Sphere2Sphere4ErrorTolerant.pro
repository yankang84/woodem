# File generated by kdevelop's qmake manager. 
# ------------------------------------------- 
# Subdir relative project main directory: ./plugins/Engine/EngineUnit/InteractionEngineUnit/NarrowInteractionGeometryEngineUnit/ErrorTolerant/Sphere2Sphere4ErrorTolerant
# Target is a library:  

LIBS += -lSphere \
        -lyade-lib-multimethods \
        -lyade-lib-factory \
        -lyade-lib-wm3-math \
        -lErrorTolerantContactModel \
        -lyade-lib-serialization \
        -rdynamic 
INCLUDEPATH = $(YADEINCLUDEPATH) 
MOC_DIR = $(YADECOMPILATIONPATH) 
UI_DIR = $(YADECOMPILATIONPATH) 
OBJECTS_DIR = $(YADECOMPILATIONPATH) 
QMAKE_LIBDIR = ../../../../../../../plugins/Data/Body/GeometricalModel/Sphere/$(YADEDYNLIBPATH) \
               ../../../../../../../libraries/yade-lib-multimethods/$(YADEDYNLIBPATH) \
               ../../../../../../../libraries/yade-lib-factory/$(YADEDYNLIBPATH) \
               ../../../../../../../libraries/yade-lib-wm3-math/$(YADEDYNLIBPATH) \
               ../../../../../../../plugins/Data/Interaction/NarrowInteractionGeometry/ErrorTolerantContactModel/$(YADEDYNLIBPATH) \
               ../../../../../../../libraries/yade-lib-serialization/$(YADEDYNLIBPATH) \
               ../../../../../../../yade/Body/Body/$(YADEDYNLIBPATH) \
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
HEADERS += Sphere2Sphere4ErrorTolerant.hpp 
SOURCES += Sphere2Sphere4ErrorTolerant.cpp 
