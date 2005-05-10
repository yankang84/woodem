# File generated by kdevelop's qmake manager. 
# ------------------------------------------- 
# Subdir relative project main directory: ./plugins/Engine/EngineUnit/InteractionEngineUnit/InteractionPhysicsEngineUnit/ElasticContactParameters/MacroMicroElasticRelationships
# Target is a library:  

LIBS += -lSDECLinkPhysics \
        -lSDECLinkGeometry \
        -lElasticContactParameters \
        -lMacroMicroContactGeometry \
        -lBodyMacroParameters \
        -rdynamic 
INCLUDEPATH = $(YADEINCLUDEPATH) 
MOC_DIR = $(YADECOMPILATIONPATH) 
UI_DIR = $(YADECOMPILATIONPATH) 
OBJECTS_DIR = $(YADECOMPILATIONPATH) 
QMAKE_LIBDIR = ../../../../../../../plugins/Data/Interaction/InteractionPhysics/SDECLinkPhysics/$(YADEDYNLIBPATH) \
               ../../../../../../../plugins/Data/Interaction/NarrowInteractionGeometry/SDECLinkGeometry/$(YADEDYNLIBPATH) \
               ../../../../../../../plugins/Data/Interaction/InteractionPhysics/ElasticContactParameters/$(YADEDYNLIBPATH) \
               ../../../../../../../plugins/Data/Interaction/NarrowInteractionGeometry/MacroMicroContactGeometry/$(YADEDYNLIBPATH) \
               ../../../../../../../plugins/Data/Body/PhysicalParameters/BodyMacroParameters/$(YADEDYNLIBPATH) \
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
HEADERS += MacroMicroElasticRelationships.hpp 
SOURCES += MacroMicroElasticRelationships.cpp 
