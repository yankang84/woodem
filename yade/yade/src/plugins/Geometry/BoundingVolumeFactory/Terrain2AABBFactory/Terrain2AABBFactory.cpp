 #include "Terrain2AABBFactory.hpp"
 #include "Terrain.hpp"
 #include "AABB.hpp"
  
void Terrain2AABBFactory::go(	const shared_ptr<BodyInteractionGeometry>& /*cm*/,
							shared_ptr<BodyBoundingVolume>& /*bv*/,
							const Se3r& 	)
{
//	shared_ptr<Terrain> t = dynamic_pointer_cast<Terrain>(cm);
	
//	bv = shared_ptr<BodyBoundingVolume>(new AABB((t->max-t->min)*0.5,(t->max+t->min)*0.5));
}	
