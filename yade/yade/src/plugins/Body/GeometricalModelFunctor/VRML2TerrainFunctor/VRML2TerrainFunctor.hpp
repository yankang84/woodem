#ifndef __TERRAINFROMWRL1FILEFACTORY_H__
#define __TERRAINFROMWRL1FILEFACTORY_H__

#include "GeometricalModelFunctor.hpp"

class VRML2TerrainFunctor : public GeometricalModelFunctor
{
	REGISTER_CLASS_NAME(VRML2TerrainFunctor);
};

REGISTER_SERIALIZABLE(VRML2TerrainFunctor,false);

#endif // __TERRAINFROMWRL1FILEFACTORY_H__
