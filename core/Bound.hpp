/*************************************************************************
*  Copyright (C) 2004 by Olivier Galizzi                                 *
*  olivier.galizzi@imag.fr                                               *
*                                                                        *
*  This program is free software; it is licensed under the terms of the  *
*  GNU General Public License v2 or later. See file LICENSE for details. *
*************************************************************************/
#pragma once

#include<yade/lib-base/yadeWm3Extra.hpp>
#include<yade/lib-serialization/Serializable.hpp>
#include<yade/lib-multimethods/Indexable.hpp>

/*! \brief Abstract interface for all bounding volumes.

	All the bounding volumes (BoundingSphere, Aabb ...) derive from this class. A bounding volume is used to speed up the
	collision detection. Instead of computing if 2 complex polyhedrons collide each other, it is much faster to first test
	if their bounding volumes (for example a Aabb) are in collision.
*/

class Bound : public Serializable, public Indexable
{
	public :
		Vector3r	 diffuseColor		/// Color of the bounding volume. Used only for drawing purpose
				,min			/// Minimum of the bounding volume
				,max;			/// Maximum of the bounding volume
		Bound(): diffuseColor(Vector3r(1,1,1)), min(Vector3r(0,0,0)), max(Vector3r(0,0,0)) {}

	REGISTER_ATTRIBUTES(Serializable,(diffuseColor));
	REGISTER_CLASS_AND_BASE(Bound,Serializable Indexable);
	REGISTER_INDEX_COUNTER(Bound);
};
REGISTER_SERIALIZABLE(Bound);
