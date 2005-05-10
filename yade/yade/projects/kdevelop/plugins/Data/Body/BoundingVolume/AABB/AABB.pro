# File generated by kdevelop's qmake manager. 
# ------------------------------------------- 
# Subdir relative project main directory: ./plugins/Data/Body/BoundingVolume/AABB
# Target is a library:  

LIBS += -lyade-lib-serialization \
        -lyade-lib-wm3-math \
        -rdynamic 
INCLUDEPATH = $(YADEINCLUDEPATH) 
MOC_DIR = $(YADECOMPILATIONPATH) 
UI_DIR = $(YADECOMPILATIONPATH) 
OBJECTS_DIR = $(YADECOMPILATIONPATH) 
QMAKE_LIBDIR = ../../../../../libraries/yade-lib-serialization/$(YADEDYNLIBPATH) \
               ../../../../../libraries/yade-lib-wm3-math/$(YADEDYNLIBPATH) \
               ../../../../../yade/Body/BoundingVolume/$(YADEDYNLIBPATH) \
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
HEADERS += AABB.hpp 
SOURCES += AABB.cpp 
