# File generated by kdevelop's qmake manager. 
# ------------------------------------------- 
# Subdir relative project main directory: ./plugins/Engine/Sensor/RenderingEngine/OpenGLRenderingEngine/GLDrawBoundingVolume/GLDrawBoundingSphere
# Target is a library:  

LIBS += -lBoundingSphere \
        -lyade-lib-opengl \
        -rdynamic 
INCLUDEPATH = $(YADEINCLUDEPATH) 
MOC_DIR = $(YADECOMPILATIONPATH) 
UI_DIR = $(YADECOMPILATIONPATH) 
OBJECTS_DIR = $(YADECOMPILATIONPATH) 
QMAKE_LIBDIR = ../../../../../../../plugins/Data/Body/BoundingVolume/BoundingSphere/$(YADEDYNLIBPATH) \
               ../../../../../../../libraries/yade-lib-opengl/$(YADEDYNLIBPATH) \
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
HEADERS += GLDrawBoundingSphere.hpp 
SOURCES += GLDrawBoundingSphere.cpp 
