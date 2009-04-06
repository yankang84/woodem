/*************************************************************************
*  Copyright (C) 2009 by Jean Francois Jerier                            *
*  jerier@geo.hmg.inpg.fr                                                *
*  Copyright (C) 2009 by Vincent Richefeu                                *
*  vincent.richefeu@hmg.inpg.fr                                          *
*                                                                        *
*  This program is free software; it is licensed under the terms of the  *
*  GNU General Public License v2 or later. See file LICENSE for details. *
*************************************************************************/

#include "SpherePadder.hpp"

int compare_neighbor_with_distance (const void * a, const void * b)
{
  double d1 = (*(neighbor_with_distance *)a).distance;
  double d2 = (*(neighbor_with_distance *)b).distance;      
  return (d1 > d2) ? 1 :-1;
}

int compare_tetra_porosity (const void * a, const void * b)
{
  double d1 = (*(tetra_porosity *)a).void_volume;
  double d2 = (*(tetra_porosity *)b).void_volume;      
  return ((d1) < (d2)) ? 1 :-1;
}

int compareDouble (const void * a, const void * b)
{
  return ( *(double*)a > *(double*)b ) ? 1 :-1;
}

SpherePadder::SpherePadder()
{
  vector <unsigned int> lst;
  unsigned int nb = 5;

  for (unsigned int i = 0 ; i <= nb ; ++i)
  {
	for (unsigned int j = i+1 ; j <= nb+1 ; ++j)
	{
	  for (unsigned int k = j+1 ; k <= nb+2 ; ++k)
	  {
		for (unsigned int l = k+1 ; l <= nb+3 ; ++l)
		{
		  lst.clear();
		  lst.push_back(i);
		  lst.push_back(j);
		  lst.push_back(k);
		  lst.push_back(l);
		  combination.push_back(lst);
		}
	  }
	}
  }
  
  n1 = n2 = n3 = n4 = n5 = n_densify = 0;
  trace_functions = true;
  meshIsPlugged = false;
  probeIsDefined = false;
  RadiusDataIsOK = RadiusIsSet = false;
  
  max_overlap_rate = 1e-4;
  virtual_radius_factor = 100.0;
}

void SpherePadder::setRadiusRatio(double r)
{
  r = fabs(r);
  if (r < 1.0) ratio = 1.0/r;
  else ratio = r;
  
  if (meshIsPlugged)
  {
	rmoy = 0.125 * mesh->mean_segment_length; // 1/8 = 0.125
	rmin = (2.0 * rmoy) / (ratio + 1.0);
	rmax = 2.0 * rmoy - rmin;
	dr = rmax - rmoy;
	RadiusDataIsOK = true;
	cout << "rmin = " << rmin << endl;
	cout << "rmax = " << rmax << endl;
  }
  else
  {
  rmin = rmax = rmoy = 0.0;
  RadiusDataIsOK = false;
  // rmin, rmax and rmoy will be calculated in plugTetraMesh
  }
  RadiusIsSet = true;
}

void SpherePadder::setRadiusRange(double min, double max)
{
  if (min > max)
  {
	rmin = max;
	rmax = min;
  }
  else
  {
	rmin = min;
	rmax = max;
  }
  ratio = rmax/rmin;
  rmoy = 0.5*(rmin+rmax);
  RadiusDataIsOK = true;
  RadiusIsSet = true;
}


void SpherePadder::plugTetraMesh (TetraMesh * pluggedMesh)
{
  mesh = pluggedMesh;
  partition.init(*mesh);
  meshIsPlugged = true;

  cout << "mesh->mean_segment_length = " << mesh->mean_segment_length << endl;
  cout << "mesh->min_segment_length  = " << mesh->min_segment_length << endl;
  cout << "mesh->max_segment_length  = " << mesh->max_segment_length << endl;
  
  if (!RadiusDataIsOK && RadiusIsSet && ratio != 0.0) setRadiusRatio(ratio);
  else cerr << "@SpherePadder::plugTetraMesh, no radius range defined!" << endl;
  
}

void SpherePadder::pad_5 ()
{
  if (mesh == 0) 
  {
    cerr << "@SpherePadder::pad_5, no mesh defined!" << endl;
    return;
  }
    
  if (!(mesh->isOrganized)) 
  {
    cerr << "@SpherePadder::pad_5, mesh is not valid!" << endl;
    return;
  }
  
  time_t start_time = clock();
  
  place_at_nodes();
  place_at_segment_middle();
  cancel_overlaps();
  place_at_faces();
  place_at_tetra_centers();
  place_at_tetra_vertexes ();

  time_t stop_time = clock();

  unsigned int nzero = 0;
  for (unsigned int i = 0 ; i < sphere.size() ; ++i)
  {
	if (sphere[i].R <= 0.0) ++nzero;
  }
  
  cerr << "Total number of spheres    = " << sphere.size() << endl;
  cerr << "Number at nodes            = " << n1 << endl;
  cerr << "Number at segments         = " << n2 << endl;
  cerr << "Number near faces          = " << n3 << endl;
  cerr << "Number near tetra centers  = " << n4 << endl;
  cerr << "Number near tetra vextexes = " << n5 << endl;
  cerr << "Number cancelled           = " << nzero << endl;

  
  float time_used = (float)(stop_time - start_time) / 1000000.0;
  cerr << "Time used = " << time_used << " s" << endl;
  
}

void SpherePadder::densify()
{
  BEGIN_FUNCTION ("Densify");
  unsigned int added = 0, back_added = 0;
  unsigned int nbfail = 0;
  unsigned int max_iter_densify = 40;
  unsigned int i;
  
  repack_null_radii();
  
  for (i = 0 ; i < max_iter_densify ; ++i)
  {

	// CRITERE BIDON !!!!! WARNING
  if ((added = iter_densify()) == back_added)
  {
	if (++nbfail == 3) { cout << "@densify, cannot add more spheres with this ratio" << endl; break; }
  }
  else nbfail = 0;
  
  cout << "iter " << i << ", nb spheres = " << sphere.size() /*- nzero*/ << ", added = " << added << endl;
  back_added = added;
  }
  
  if (i == max_iter_densify) cout << "@densify, maximum number of iteration reached" << endl;
  
  END_FUNCTION;
}

void SpherePadder::repack_null_radii() // TODO FIXME loop until target solid fraction is reached
{  
  for (unsigned int i = 0 ; i < sphere.size() ; i++)
  {
	if (sphere[i].R > 0.0) continue;
    place_sphere_4contacts(i);
  }
}

unsigned int SpherePadder::iter_densify(unsigned int nb_check)   
{
  unsigned int nb_added = 0, total_added = 0;
  tetra_porosity P;
  Sphere S;
  S.type = FROM_TRIANGULATION;
  unsigned int ns = sphere.size();
  unsigned int failure;
  unsigned int nbVirtual;
  //double Volume_min = 1.333333333*M_PI*rmin*rmin*rmin;
  
  // TODO add bool VirtualSpheresOK

  triangulation.clear();
  for (unsigned int i = 0 ; i < sphere.size() ; i++)
  {
	if (sphere[i].R <= 0.0) continue;
	triangulation.insert_node(sphere[i].x, sphere[i].y, sphere[i].z, i, (sphere[i].type == VIRTUAL));
  }
  if (triangulation.has_no_cells()) return total_added;
  
  tetra_porosities.clear();
  triangulation.init_current_tetrahedron();
  do
  {
	triangulation.current_tetrahedron_get_nodes(P.id1,P.id2,P.id3,P.id4);
	if (P.id1 >= ns || P.id2 >= ns || P.id3 >= ns || P.id4 >= ns) continue; // FIXME why ?
	  
	nbVirtual = 0;
	if (sphere[P.id1].type == VIRTUAL) ++nbVirtual; 
	if (sphere[P.id2].type == VIRTUAL) ++nbVirtual;
	if (sphere[P.id3].type == VIRTUAL) ++nbVirtual;
	if (sphere[P.id4].type == VIRTUAL) ++nbVirtual;
	if (nbVirtual == 4) continue;

/*
	if (squared_distance_centre_spheres(P.id1, P.id2) > 0.01) continue;
	if (squared_distance_centre_spheres(P.id1, P.id3) > 0.01) continue;
	if (squared_distance_centre_spheres(P.id1, P.id4) > 0.01) continue;
	if (squared_distance_centre_spheres(P.id2, P.id3) > 0.01) continue;
	if (squared_distance_centre_spheres(P.id2, P.id4) > 0.01) continue;
	if (squared_distance_centre_spheres(P.id3, P.id4) > 0.01) continue;
*/

	P.volume = triangulation.current_tetrahedron_get_volume();
	P.void_volume = P.volume - solid_volume_of_tetrahedron(sphere[P.id1], sphere[P.id2], sphere[P.id3], sphere[P.id4]);
	if (P.void_volume > /*Volume_min*/ 0.0 || nbVirtual > 0)
	{
	  tetra_porosities.push_back(P);
	}
  } while (triangulation.next_tetrahedron());
  
  // sort tetrahdrons from bigger to smaller void volumes 
  qsort(&(tetra_porosities[0]),tetra_porosities.size(),sizeof(tetra_porosity),compare_tetra_porosity);

  for (unsigned int i = 0 ; i < tetra_porosities.size() ; i++)
  {	
	failure = place_fifth_sphere(tetra_porosities[i].id1,tetra_porosities[i].id2,tetra_porosities[i].id3,tetra_porosities[i].id4,S);

	if (!failure)
	{
	  failure = check_overlaps(S,ns+1); // ns+1 i.e. on exclut aucune sphere
	}
	else // failure 
	{
// 	  Sphere & S1 = sphere[tetra_porosities[i].id1];
// 	  Sphere & S2 = sphere[tetra_porosities[i].id2];
// 	  Sphere & S3 = sphere[tetra_porosities[i].id3];
// 	  Sphere & S4 = sphere[tetra_porosities[i].id4];

	  /*
	  CGAL::weighted_circumcenterC3 (
	                                 S1.x, S1.y, S1.z, S1.R * S1.R,
									 S2.x, S2.y, S2.z, S2.R * S2.R,
									 S3.x, S3.y, S3.z, S3.R * S3.R,
									 S4.x, S4.y, S4.z, S4.R * S4.R,
									 S.x, S.y, S.z
									 );
	  */

      

// 	  double distance_min = distance_centre_spheres(S,S1) - S1.R;
// 	  double distance;
// 	  distance_min = (distance_min < (distance = distance_centre_spheres(S,S2) - S2.R)) ? distance_min : distance;
// 	  distance_min = (distance_min < (distance = distance_centre_spheres(S,S3) - S3.R)) ? distance_min : distance;
// 	  distance_min = (distance_min < (distance = distance_centre_spheres(S,S4) - S4.R)) ? distance_min : distance;
// 	  S.R = distance_min;
// 	  if (S.R > rmax) S.R = rmax;
	  // TODO mettre en contact

      S.R = rmin; // test

      //if (S.R >= rmin)
	  {
//failure = 0;
		failure = check_overlaps(S,ns+10);
	  }
	}
	
	if(!failure)
	{
	  vector<neighbor_with_distance> neighbor;
	  build_sorted_list_of_neighbors(S, neighbor);
	  
	  S.R += neighbor[0].distance;
      
	  if (S.R >= rmin && S.R <= rmax)
	  {
		sphere.push_back(S);++(n_densify);
		partition.add(ns,S.x,S.y,S.z);
		triangulation.insert_node(S.x,S.y,S.z,ns,false); // necessary to compute mean solid fraction
		++ns; ++nb_added; ++total_added;
	  }
	}

	// check if we must stop
	if (nb_added >= nb_check)
	{
	  //cout << "check, total_added = " << total_added << endl;
	  nb_added = 0;
	  // getMeanSolidFraction();
	}
  }

return total_added;
}

void SpherePadder::save_tri_mgpost (const char* name)
{
  // triangulation
  triangulation.clear();
  for (unsigned int i = 0 ; i < sphere.size() ; i++)
  {
	if (sphere[i].R <= 0.0) continue;
	triangulation.insert_node(sphere[i].x, sphere[i].y, sphere[i].z, i, (sphere[i].type == VIRTUAL));
  }
  if (triangulation.has_no_cells()) return;

  ofstream fmgpost(name);
  fmgpost << "<?xml version=\"1.0\"?>" << endl
  << " <mgpost mode=\"3D\">" << endl
  << "  <state id=\"" << 1 << "\" time=\"" << 0.0 << "\">" << endl;

  double xp,yp,zp,rad,void_volume;
  unsigned int id1,id2,id3,id4,i=0;
  tetra_porosities.clear();
  triangulation.init_current_tetrahedron();
  do
  {
	triangulation.current_tetrahedron_get_nodes(id1,id2,id3,id4);
	//if(sphere[id1].type == VIRTUAL && sphere[id2].type == VIRTUAL && sphere[id3].type == VIRTUAL && sphere[id4].type == VIRTUAL) continue;
	
	xp = 0.25*(sphere[id1].x+sphere[id2].x+sphere[id3].x+sphere[id4].x);
	yp = 0.25*(sphere[id1].y+sphere[id2].y+sphere[id3].y+sphere[id4].y);
	zp = 0.25*(sphere[id1].z+sphere[id2].z+sphere[id3].z+sphere[id4].z);
	rad = (sphere[id1].R>sphere[id2].R)?sphere[id1].R:sphere[id2].R;
	rad = (rad>sphere[id3].R)?rad:sphere[id3].R;
	rad = (rad>sphere[id4].R)?rad:sphere[id4].R;

	void_volume = triangulation.current_tetrahedron_get_volume() - solid_volume_of_tetrahedron(sphere[id1], sphere[id2], sphere[id3], sphere[id4]);
	if (void_volume<0.0) void_volume = 0.0;
	
	fmgpost << "   <body>" << endl;
	fmgpost << "    <POLYE id=\"" << ++i << "\" r=\"" << rad << "\">" << endl
	<< "     <position x=\"" << xp << "\" y=\"" << yp << "\" z=\"" << zp << "\"/>" << endl
	//<< "     <velocity rot=\"" << void_volume << "\"/>" << endl
	<< "     <velocity rot=\"" << triangulation.current_tetrahedron_get_volume() << "\"/>" << endl
	<< "     <node x=\""<< sphere[id1].x-xp << "\" y=\"" << sphere[id1].y-yp << "\" z=\"" << sphere[id1].z-zp << "\"/>" << endl
	<< "     <node x=\""<< sphere[id2].x-xp << "\" y=\"" << sphere[id2].y-yp << "\" z=\"" << sphere[id2].z-zp << "\"/>" << endl
	<< "     <node x=\""<< sphere[id3].x-xp << "\" y=\"" << sphere[id3].y-yp << "\" z=\"" << sphere[id3].z-zp << "\"/>" << endl
	<< "     <node x=\""<< sphere[id4].x-xp << "\" y=\"" << sphere[id4].y-yp << "\" z=\"" << sphere[id4].z-zp << "\"/>" << endl
	<< "     <face n1=\"0\" n2=\"1\" n3=\"2\"/>" << endl
	<< "     <face n1=\"0\" n2=\"2\" n3=\"3\"/>" << endl
	<< "     <face n1=\"0\" n2=\"3\" n3=\"1\"/>" << endl
	<< "     <face n1=\"1\" n2=\"3\" n3=\"2\"/>" << endl
	<< "    </POLYE>" << endl << flush;
	fmgpost << "   </body>" << endl;
  } while (triangulation.next_tetrahedron());
  
  fmgpost << "  </state>" << endl
  << " </mgpost>" << endl;

}

void SpherePadder::save_mgpost (const char* name)
{
  BEGIN_FUNCTION ("Save mgp");
  
  ofstream fmgpost(name);
  
  double xtrans = mesh->xtrans;
  double ytrans = mesh->ytrans;
  double ztrans = mesh->ztrans;
  
  fmgpost << "<?xml version=\"1.0\"?>" << endl
      << " <mgpost mode=\"3D\">" << endl
	  // Note that number of newcolors is limited in mgpost
      << "  <newcolor name=\"at nodes\"/>" << endl
      << "  <newcolor name=\"at segments\"/>" << endl   
      << "  <newcolor name=\"at faces\"/>" << endl
      << "  <newcolor name=\"at tetra centers\"/>" << endl
      << "  <newcolor name=\"at tetra vertexes\"/>" << endl
	  << "  <newcolor name=\"insered by user\"/>" << endl
	  << "  <newcolor name=\"from triangulation\"/>" << endl
      << "  <state id=\"" << 1 
      << "\" time=\"" << 0.0 << "\">" << endl;

  for (unsigned int i = 0 ; i < sphere.size() ; ++i)
  {
	// the sphere with R=0 that are placed at nodes are saved because mgpost needs them
	// for the display of tetrahdrons.
    if (sphere[i].R <= 0.0 && sphere[i].type != AT_NODE) continue; 
	if (sphere[i].type == VIRTUAL) continue;

	
    fmgpost << "   <body>" << endl;
    fmgpost << "    <SPHER id=\"" << i+1 << "\" col=\"" << sphere[i].type << "\" r=\"" << sphere[i].R << "\">" << endl
        << "     <position x=\"" << sphere[i].x + xtrans << "\" y=\"" 
        << sphere[i].y + ytrans << "\" z=\"" << sphere[i].z + ztrans << "\"/>" << endl   
        << "    </SPHER>" << endl << flush;

    // This is not the contact network but rather the tetrahedrons 
    if (i < mesh->node.size())
	{
      for (unsigned int s = 0 ; s < mesh->segment.size() ; ++s)
	  {
		if (mesh->segment[s].nodeId[0] == i)
		{
		if (mesh->segment[s].nodeId[1] < mesh->node.size())
		  fmgpost << "    <SPSPx antac=\"" << mesh->segment[s].nodeId[1] + 1 << "\"/>" << endl;
		}
	  }
	}

    fmgpost << "   </body>" << endl;
  }

  fmgpost << "  </state>" << endl
      << " </mgpost>" << endl;
                
  END_FUNCTION;
}
	
void SpherePadder::save_Rxyz (const char* name)
{
  BEGIN_FUNCTION("Save Rxyz");
  
  ofstream file(name);
  
  double xtrans = mesh->xtrans;
  double ytrans = mesh->ytrans;
  double ztrans = mesh->ztrans;

  for (unsigned int i = 0 ; i < sphere.size() ; ++i)
  {
	if (sphere[i].R <= 0.0) continue;
    file << sphere[i].R << " " << sphere[i].x + xtrans << " " << sphere[i].y + ytrans << " " << sphere[i].z + ztrans << endl;
  }
                
  END_FUNCTION;
}

void SpherePadder::save_granulo(const char* name)
{
  vector<double> D;
  for (unsigned int i = 0 ; i < sphere.size() ; ++i)
  {
    if (sphere[i].R <= 0.0) continue; 
    D.push_back(2.0 * sphere[i].R);
  }
  qsort (&(D[0]), D.size(), sizeof(double), compareDouble);
  
  ofstream file(name);
  double inv_N = 1.0 / (double)D.size();
  for (unsigned int i = 0 ; i < D.size() ; ++i)
  {
    file << D[i] << ' ' << (double)i * inv_N << endl;
  }
}
        
void SpherePadder::place_at_nodes ()
{
  BEGIN_FUNCTION("Place at nodes");
        
  unsigned int segId;
  Sphere S;
  S.type = AT_NODE;
        
  for (unsigned int n = 0 ; n < mesh->node.size() ; ++n)
  {
   if (mesh->node[n].segmentOwner.empty()) continue;
  
    S.x = mesh->node[n].x;
    S.y = mesh->node[n].y;
    S.z = mesh->node[n].z;
    S.R = mesh->segment[ mesh->node[n].segmentOwner[0] ].length;
    for (unsigned int i = 1 ; i < mesh->node[n].segmentOwner.size() ; ++i)
    {
      segId = mesh->node[n].segmentOwner[i];
      S.R = (S.R < mesh->segment[segId].length) ? S.R : mesh->segment[segId].length;
    }       
    S.R /= 4.0;
	if (S.R > rmax) S.R = rmax;
	if (S.R < rmin) S.R = rmin;
                
    sphere.push_back(S); ++(n1); 
    //check_inProbe(n);compacity_in_probe(n);
    partition.add(n,S.x,S.y,S.z);
  }
        
  END_FUNCTION;
}

void SpherePadder::place_at_segment_middle ()
{       
  BEGIN_FUNCTION("Place at segment middle");
  Sphere S;
  S.type = AT_SEGMENT;
  double x1,y1,z1;
  double x2,y2,z2;
  unsigned int id1,id2;
  unsigned int ns = sphere.size();
        
  for (unsigned int s = 0 ; s < mesh->segment.size() ; ++s)
  {
    id1 = mesh->segment[s].nodeId[0];
    id2 = mesh->segment[s].nodeId[1];
                
    x1  = mesh->node[id1].x;
    y1  = mesh->node[id1].y;
    z1  = mesh->node[id1].z;
                
    x2  = mesh->node[id2].x;
    y2  = mesh->node[id2].y;
    z2  = mesh->node[id2].z;
                
    S.x = 0.5 * (x1 + x2);
    S.y = 0.5 * (y1 + y2);
    S.z = 0.5 * (z1 + z2);
    S.R = 0.125 * mesh->segment[s].length;
    if (S.R < rmin) S.R = rmin;
    if (S.R > rmax) S.R = rmoy + dr * (double)rand()/(double)RAND_MAX;
    
    sphere.push_back(S); ++(n2); 
    partition.add(ns,S.x,S.y,S.z);
                
    mesh->segment[s].sphereId = ns;
    ++ns;
                
  }       
  END_FUNCTION;   
}


void SpherePadder::place_at_faces ()
{
  BEGIN_FUNCTION("Place at faces");
 
  // FIXME move the following loops in TetraMesh or at the end of place_at_segment_middle ??
  unsigned int sphereId,faceId;
  for (unsigned int s = 0 ; s < mesh->segment.size() ; ++s)
  {
    sphereId = mesh->segment[s].sphereId;
    for (unsigned int f = 0 ; f < mesh->segment[s].faceOwner.size() ; ++f)
    {
      faceId = mesh->segment[s].faceOwner[f];
      mesh->face[ faceId ].sphereId.push_back( sphereId );
    }
  }
        
  Sphere S;
  S.type = AT_FACE;

  unsigned int ns = sphere.size();
  const double div3 = 0.3333333333333;
  Sphere S1,S2,S3;

  for (unsigned int f = 0 ; f < mesh->face.size() ; ++f)
  {
    S1 = sphere[ mesh->face[f].sphereId[0] ];
    S2 = sphere[ mesh->face[f].sphereId[1] ];
    S3 = sphere[ mesh->face[f].sphereId[2] ];

    S.x = div3 * (S1.x + S2.x + S3.x);
    S.y = div3 * (S1.y + S2.y + S3.y);
    S.z = div3 * (S1.z + S2.z + S3.z);                
    S.R = rmin;
    
    sphere.push_back(S); ++(n3);
    place_sphere_4contacts(ns);
    ++ns;
  }
        
  END_FUNCTION;  
}


void SpherePadder::place_at_tetra_centers ()
{
  BEGIN_FUNCTION("Place at tetra centers");
    
  Sphere S;
  S.type = AT_TETRA_CENTER;
  Tetraedre T;
  
  unsigned int ns = sphere.size(); 
  Node N1,N2,N3,N4;

  for (unsigned int t = 0 ; t < mesh->tetraedre.size() ; ++t)
  {
    T = mesh->tetraedre[t];
    N1 = mesh->node[T.nodeId[0]];
    N2 = mesh->node[T.nodeId[1]];
    N3 = mesh->node[T.nodeId[2]];
    N4 = mesh->node[T.nodeId[3]];
    
    S.x = 0.25 * (N1.x + N2.x + N3.x + N4.x); 
    S.y = 0.25 * (N1.y + N2.y + N3.y + N4.y); 
    S.z = 0.25 * (N1.z + N2.z + N3.z + N4.z); 

    S.R = rmin;
                
    sphere.push_back(S); ++(n4);
    place_sphere_4contacts(ns);
    ++ns;
  }
        
  END_FUNCTION;  
}

void SpherePadder::place_at_tetra_vertexes ()
{
  BEGIN_FUNCTION("Place at tetra vertexes");
    
  Sphere S;
  S.type = AT_TETRA_VERTEX;
  Tetraedre T;
  
  unsigned int ns = sphere.size();
  Node N1,N2,N3,N4;
  double centre[3];

  for (unsigned int t = 0 ; t < mesh->tetraedre.size() ; ++t)
  {
    T = mesh->tetraedre[t];
    N1 = mesh->node[T.nodeId[0]];
    N2 = mesh->node[T.nodeId[1]];
    N3 = mesh->node[T.nodeId[2]];
    N4 = mesh->node[T.nodeId[3]];
    
    centre[0] = 0.25 * (N1.x + N2.x + N3.x + N4.x); 
    centre[1] = 0.25 * (N1.y + N2.y + N3.y + N4.y); 
    centre[2] = 0.25 * (N1.z + N2.z + N3.z + N4.z); 

    S.R = rmin;
                
    double pondere = 0.333333333; // FIXME parametrable ?
    for (unsigned int n = 0 ; n < 4 ; ++n)
    {
      S.x = pondere * mesh->node[ T.nodeId[n] ].x + (1.0 - pondere) * centre[0];
      S.y = pondere * mesh->node[ T.nodeId[n] ].y + (1.0 - pondere) * centre[1];
      S.z = pondere * mesh->node[ T.nodeId[n] ].z + (1.0 - pondere) * centre[2];
      
      sphere.push_back(S); ++(n5);
	  place_sphere_4contacts(ns);
	  ++ns;
    }
  }
        
  END_FUNCTION; 
}

double SpherePadder::squared_distance_centre_spheres(unsigned int i, unsigned int j)
{
  double lx,ly,lz;
  lx  = sphere[j].x - sphere[i].x;
  ly  = sphere[j].y - sphere[i].y;
  lz  = sphere[j].z - sphere[i].z;
  return ((lx*lx + ly*ly + lz*lz));
}

// deprecated
double SpherePadder::distance_spheres(unsigned int i, unsigned int j)
{
  double lx,ly,lz;
  lx  = sphere[j].x - sphere[i].x;
  ly  = sphere[j].y - sphere[i].y;
  lz  = sphere[j].z - sphere[i].z;
  return (sqrt(lx*lx + ly*ly + lz*lz) - sphere[i].R - sphere[j].R);
}

double SpherePadder::distance_spheres(Sphere & S1, Sphere & S2)
{
  double lx,ly,lz;
  lx  = S2.x - S1.x;
  ly  = S2.y - S1.y;
  lz  = S2.z - S1.z;
  return (sqrt(lx*lx + ly*ly + lz*lz) - S1.R - S2.R);
}

double SpherePadder::distance_centre_spheres(Sphere& S1, Sphere& S2)
{
  double lx,ly,lz;
  lx  = S2.x - S1.x;
  ly  = S2.y - S1.y;
  lz  = S2.z - S1.z;
  return (sqrt(lx*lx + ly*ly + lz*lz));
}

void SpherePadder::build_sorted_list_of_neighbors(Sphere & S, vector<neighbor_with_distance> & neighbor)
{
  neighbor_with_distance N;
  
  unsigned int id;
  Cell current_cell;
  
  partition.locateCellOf(S.x,S.y,S.z);
  
  // Build the local list of neighbors
  for (unsigned int i = partition.i_down() ; i <= partition.i_up() ; ++i)
  {
	for (unsigned int j = partition.j_down() ; j <= partition.j_up() ; ++j)
	{
	  for (unsigned int k = partition.k_down() ; k <= partition.k_up() ; ++k)
	  {
		
		current_cell = partition.get_cell(i,j,k);
		for (unsigned int s = 0 ; s < current_cell.sphereId.size() ; ++s)
		{
		  id = current_cell.sphereId[s];
		  //if (id != sphereId)
		  {
			N.sphereId = id;
			N.distance = distance_spheres(S,sphere[id]);
			neighbor.push_back(N);
		  }
		}
		
	  }
	}
  }
  
  qsort(&(neighbor[0]),neighbor.size(),sizeof(neighbor_with_distance),compare_neighbor_with_distance);
}

void SpherePadder::build_sorted_list_of_neighbors(unsigned int sphereId, vector<neighbor_with_distance> & neighbor)
{
  neighbor_with_distance N;
  
  unsigned int id;
  Cell current_cell;
  
  partition.locateCellOf(sphere[sphereId].x,sphere[sphereId].y,sphere[sphereId].z);
  
  // Build the local list of neighbors
  for (unsigned int i = partition.i_down() ; i <= partition.i_up() ; ++i)
  {
	for (unsigned int j = partition.j_down() ; j <= partition.j_up() ; ++j)
	{
	  for (unsigned int k = partition.k_down() ; k <= partition.k_up() ; ++k)
	  {
		
		current_cell = partition.get_cell(i,j,k);
		for (unsigned int s = 0 ; s < current_cell.sphereId.size() ; ++s)
		{
		  id = current_cell.sphereId[s];
		  if (id != sphereId)
		  {
			N.sphereId = id;
			N.distance = distance_spheres(sphereId,id);
			neighbor.push_back(N);
		  }
		}
		
	  }
	}
  }
  
  qsort(&(neighbor[0]),neighbor.size(),sizeof(neighbor_with_distance),compare_neighbor_with_distance);
}

unsigned int SpherePadder::place_sphere_4contacts (unsigned int sphereId, unsigned int nb_combi_max)
{ 
  Sphere S = sphere[sphereId];
  Sphere Sbackup;

  vector<neighbor_with_distance> neighbor;
  build_sorted_list_of_neighbors(sphereId, neighbor);
  
  S.R += neighbor[0].distance;
  if (S.R >= rmin && S.R <= rmax) sphere[sphereId].R = S.R;
  else if (S.R > rmax)            sphere[sphereId].R = rmax;
  else                            sphere[sphereId].R = 0.0;

  vector<vector<unsigned int> > possible_combination;
  for (unsigned int c = 0 ; c < combination.size() ; ++c)
  {
    if (combination[c][0] >= neighbor.size()) continue;
    if (combination[c][1] >= neighbor.size()) continue;
    if (combination[c][2] >= neighbor.size()) continue;
    if (combination[c][3] >= neighbor.size()) continue;
    possible_combination.push_back(combination[c]);
  }
  
  unsigned int s1,s2,s3,s4;
  unsigned int failure;
  unsigned int nb_combi;
  nb_combi = (nb_combi_max < possible_combination.size()) ? nb_combi_max : possible_combination.size();
  Sbackup = S;
  for (unsigned int c = 0 ; c < nb_combi ; ++c)
  {    
    s1 = neighbor[ possible_combination[c][0] ].sphereId;
    s2 = neighbor[ possible_combination[c][1] ].sphereId;
    s3 = neighbor[ possible_combination[c][2] ].sphereId;
    s4 = neighbor[ possible_combination[c][3] ].sphereId;
    
    S = Sbackup;
    failure = place_fifth_sphere(s1,s2,s3,s4,S);

    if (!failure)
	  failure = check_overlaps(S, sphereId);
	else continue;

    if (!failure)
    {
      sphere[sphereId].x = S.x;
      sphere[sphereId].y = S.y;
      sphere[sphereId].z = S.z;
      sphere[sphereId].R = S.R;
      partition.add(sphereId,S.x,S.y,S.z);
      return 1;
    }

  }

  if (sphere[sphereId].R > 0.0) partition.add(sphereId,S.x,S.y,S.z);
  return 0;
}

unsigned int SpherePadder::check_overlaps(Sphere & S, unsigned int excludedId)
{
  unsigned int id;
  Cell current_cell;
  
  partition.locateCellOf(S.x,S.y,S.z);
  for (unsigned int i = partition.i_down() ; i <= partition.i_up() ; ++i)
  {
	for (unsigned int j = partition.j_down() ; j <= partition.j_up() ; ++j)
	{
	  for (unsigned int k = partition.k_down() ; k <= partition.k_up() ; ++k)
	  {
		current_cell = partition.get_cell(i,j,k);
		for (unsigned int s = 0 ; s < current_cell.sphereId.size() ; ++s)
		{
		  id = current_cell.sphereId[s];
		  if (id != excludedId && sphere[id].R > 0.0)
		  {
			if (distance_spheres(S,sphere[id]) < (-max_overlap_rate * rmin)) { return 128; }
		  }
		}
	  }
	}
  }
  return 0;
}

double SpherePadder::distance_vector3 (double V1[],double V2[])
{
  double D[3];
  D[0] = V2[0] - V1[0];
  D[1] = V2[1] - V1[1];
  D[2] = V2[2] - V1[2];
  return ( sqrt(D[0]*D[0] + D[1]*D[1] + D[2]*D[2]) );
}

unsigned int SpherePadder::place_fifth_sphere(unsigned int s1, unsigned int s2, unsigned int s3, unsigned int s4, Sphere& S)
{
  double C1[3],C2[3],C3[3],C4[3];
  double R1,R2,R3,R4;
  C1[0] = sphere[s1].x ; C1[1] = sphere[s1].y ; C1[2] = sphere[s1].z ; R1 = sphere[s1].R;  
  C2[0] = sphere[s2].x ; C2[1] = sphere[s2].y ; C2[2] = sphere[s2].z ; R2 = sphere[s2].R; 
  C3[0] = sphere[s3].x ; C3[1] = sphere[s3].y ; C3[2] = sphere[s3].z ; R3 = sphere[s3].R; 
  C4[0] = sphere[s4].x ; C4[1] = sphere[s4].y ; C4[2] = sphere[s4].z ; R4 = sphere[s4].R;

  // rougth estimate of the position
  // TODO 
  
  unsigned int fail_det          = 0x01;
  unsigned int fail_delta        = 0x02;
  unsigned int fail_radius       = 0x04;
  unsigned int fail_overlap      = 0x08;
  unsigned int fail_gap          = 0x10;
  unsigned int fail_radius_range = 0x20;
  unsigned int fail_NaN          = 0x40;

  // (x-x1)^2 + (y-y1)^2 + (z-z1)^2 = (r+r1)^2   (1)
  // (x-x2)^2 + (y-y2)^2 + (z-z2)^2 = (r+r2)^2   (2)
  // (x-x3)^2 + (y-y3)^2 + (z-z3)^2 = (r+r3)^2   (3)
  // (x-x4)^2 + (y-y4)^2 + (z-z4)^2 = (r+r4)^2   (4)

  // (2)-(1)
  double a = 2.0 * (C1[0] - C2[0]);
  double b = 2.0 * (C1[1] - C2[1]);
  double c = 2.0 * (C1[2] - C2[2]);
  double d = 2.0 * (R1 - R2);
  double e = (C1[0]*C1[0] + C1[1]*C1[1] + C1[2]*C1[2] - R1*R1) - (C2[0]*C2[0] + C2[1]*C2[1] + C2[2]*C2[2] - R2*R2);

  // (3)-(1)
  double aa = 2.0 * (C1[0] - C3[0]);
  double bb = 2.0 * (C1[1] - C3[1]);
  double cc = 2.0 * (C1[2] - C3[2]);
  double dd = 2.0 * (R1 - R3);
  double ee = (C1[0]*C1[0] + C1[1]*C1[1] + C1[2]*C1[2] - R1*R1) - (C3[0]*C3[0] + C3[1]*C3[1] + C3[2]*C3[2] - R3*R3);

  // (4)-(1)
  double aaa = 2.0 *(C1[0] - C4[0]);
  double bbb = 2.0 *(C1[1] - C4[1]);
  double ccc = 2.0 *(C1[2] - C4[2]);
  double ddd = 2.0 *(R1 - R4);
  double eee = (C1[0]*C1[0] + C1[1]*C1[1] + C1[2]*C1[2] - R1*R1) - (C4[0]*C4[0] + C4[1]*C4[1] + C4[2]*C4[2] - R4*R4);

  // compute the determinant of matrix A (system AX = B)
  //      [a  ,  b,  c];    [x]        [e  -  d*r]
  //  A = [aa ,bb ,cc ];  X=[y]   B(r)=[ee - dd*r]
  //      [aaa,bbb,ccc];    [z]        [eee-ddd*r]

  double DET = a*(bb*ccc-bbb*cc) - aa*(b*ccc-bbb*c) + aaa*(b*cc-bb*c);
  double R = 0.0;
  double centre[3];
  if (DET != 0.0)
  {
    //        [a11,a12,a13]
    // A^-1 = [a21,a22,a23] * 1/det(A)
    //        [a31,a32,a33]  
          
    double inv_DET = 1.0/DET;
    double a11 =  (bb*ccc-bbb*cc) * inv_DET;
    double a12 = -(b*ccc-bbb*c)   * inv_DET;
    double a13 =  (b*cc-bb*c)     * inv_DET;
    double a21 = -(aa*ccc-aaa*cc) * inv_DET;
    double a22 =  (a*ccc-aaa*c)   * inv_DET;
    double a23 = -(a*cc-aa*c)     * inv_DET;
    double a31 =  (aa*bbb-aaa*bb) * inv_DET;
    double a32 = -(a*bbb-aaa*b)   * inv_DET;
    double a33 =  (a*bb-aa*b)     * inv_DET;

	// A^-1 B(r)
    double xa = -(a11*d + a12*dd + a13*ddd);
    double xb =  (a11*e + a12*ee + a13*eee);

    double ya = -(a21*d + a22*dd + a23*ddd);
    double yb =  (a21*e + a22*ee + a23*eee);

    double za = -(a31*d + a32*dd + a33*ddd);
    double zb =  (a31*e + a32*ee + a33*eee);
	
    // Replace x, y and z in Equation (1) and solve the second order equation A*r^2 + B*r + C = 0

    double A = xa*xa + ya*ya + za*za - 1.0;
    double B = 2.0*(xa*(xb-C1[0])) + 2.0*(ya*(yb-C1[1])) + 2.0*(za*(zb-C1[2])) - 2.0*R1;
    double C = (xb-C1[0])*(xb-C1[0]) + (yb-C1[1])*(yb-C1[1]) + (zb-C1[2])*(zb-C1[2]) - R1*R1;

    double DELTA = B*B - 4.0*A*C;
    double RR1,RR2;

    if (DELTA >= 0.0) // && A != 0.0
    {
      double inv_2A = 0.5/A;
      double sqrt_DELTA = sqrt(DELTA);
      RR1 = (-B + sqrt_DELTA) * inv_2A;
      RR2 = (-B - sqrt_DELTA) * inv_2A;
    }
    else return fail_delta;

    if      (RR1 > 0.0) R = RR1;
    else if (RR2 > 0.0) R = RR2;
    else if (RR1 <= 0.0 && RR2 <= 0.0) return fail_radius;
    
    if (R < rmin || R > rmax) return fail_radius_range;

    centre[0] = xa * R + xb;
    centre[1] = ya * R + yb;
    centre[2] = za * R + zb;
  }
  else return fail_det;

  S.x = centre[0];
  S.y = centre[1];
  S.z = centre[2];
  S.R = R;
  
  // FIXME do not use sqrt to speed up... (squared_distance_vector3)
  // for the moment it is not critical
  
  // Check interpenetration between spheres
  double distance1 = distance_vector3 (centre,C1) - (R + R1);
  double distance2 = distance_vector3 (centre,C2) - (R + R2);
  double distance3 = distance_vector3 (centre,C3) - (R + R3);
  double distance4 = distance_vector3 (centre,C4) - (R + R4);
  
//   double half_distance_rate = -0.5 * max_overlap_rate;
//   if (     ( distance1 < half_distance_rate * (R + R1)) 
//         || ( distance2 < half_distance_rate * (R + R2))
//         || ( distance3 < half_distance_rate * (R + R3)) 
//         || ( distance4 < half_distance_rate * (R + R4)) )
//   { return fail_overlap; }

  double max_overlap = -max_overlap_rate * rmin;
  if ( ( distance1 < max_overlap)
	|| ( distance2 < max_overlap)
	|| ( distance3 < max_overlap)
	|| ( distance4 < max_overlap) )
  { return fail_overlap; }
  
  // The gap between spheres must not be too large
  double distance_max = max_overlap_rate * rmin;
  if ( ( distance1 > distance_max)
    || ( distance2 > distance_max)
    || ( distance3 > distance_max)
    || ( distance4 > distance_max) )
  { return fail_gap; }
  
  // Check if there is NaN 
  if ( (centre[0] != centre[0])
    || (centre[1] != centre[1])
    || (centre[2] != centre[2])
    || (R != R))
  { return fail_NaN; }


  //S.R = R;
  return 0;
}


 void SpherePadder::place_virtual_spheres() // WARNING there is a bug in this function (TODO include modifications of Philippe Marin)
{
  
  BEGIN_FUNCTION("Place virtual spheres...");
    
  Tetraedre current_tetra, tetra_neighbor;
  
  unsigned int sphereId, current_tetra_id, n1, n2, n3, n4, s1, s2, s3, s4;
  const double div3 = 0.3333333333333;
  Sphere S1,S2,S3,S4,S;
  double sphere_virtual_radius, k;
  double scalar_product;
  double vect1 [3], vect2 [3], vect3 [3], perpendicular_vector [3];

  bool added;
  vector<unsigned int> j_ok;
   
  sphere_virtual_radius = (mesh->mean_segment_length) * virtual_radius_factor;
  k = sphere_virtual_radius;
  sphereId = sphere.size();
  
  for (unsigned int f = 0 ; f < mesh->face.size() ; ++f)
  {

    if (mesh->face[f].belongBoundary)
    {  
      current_tetra_id = mesh->face[f].tetraOwner[0];
      current_tetra = mesh->tetraedre[current_tetra_id];
    
      n1 = current_tetra.nodeId[0];
      n2 = current_tetra.nodeId[1];
      n3 = current_tetra.nodeId[2];
      n4 = current_tetra.nodeId[3];
      
      s1 = mesh->face[f].nodeId[0];
      s2 = mesh->face[f].nodeId[1];
      s3 = mesh->face[f].nodeId[2];
    
      if ((n1 != s1) && (n1 != s2) && (n1 != s3))
      {
        s4 = n1;
      }
      else if ((n2 != s1) && (n2 != s2) && (n2 != s3))
      {
        s4 = n2;
      }    
      else if ((n3 != s1) && (n3 != s2) && (n3 != s3))
      {
        s4 = n3;
      }    
      else
      {
        s4 = n4;
      }
   
      S1 = sphere[ s1 ];
      S2 = sphere[ s2 ];
      S3 = sphere[ s3 ];
      S4 = sphere[ s4 ];  
    
      const double inv_distance_sphere_1_2 = 1.0 / distance_centre_spheres( S1, S2);
      const double inv_distance_sphere_1_3 = 1.0 / distance_centre_spheres( S1, S3);
      const double inv_distance_sphere_1_4 = 1.0 / distance_centre_spheres( S1, S4);

      vect1 [0] = (S1.x - S2.x) * inv_distance_sphere_1_2;
      vect1 [1] = (S1.y - S2.y) * inv_distance_sphere_1_2;
      vect1 [2] = (S1.z - S2.z) * inv_distance_sphere_1_2;

      vect2 [0] = (S1.x - S3.x) * inv_distance_sphere_1_3;
      vect2 [1] = (S1.y - S3.y) * inv_distance_sphere_1_3;
      vect2 [2] = (S1.z - S3.z) * inv_distance_sphere_1_3;

      vect3 [0] = (S1.x - S4.x) * inv_distance_sphere_1_4;
      vect3 [1] = (S1.y - S4.y) * inv_distance_sphere_1_4;
      vect3 [2] = (S1.z - S4.z) * inv_distance_sphere_1_4;
    

      perpendicular_vector [0] = (vect1 [1] * vect2 [2]) - (vect1 [2] * vect2 [1]);  
      perpendicular_vector [1] = (vect1 [2] * vect2 [0]) - (vect1 [0] * vect2 [2]);
      perpendicular_vector [2] = (vect1 [0] * vect2 [1]) - (vect1 [1] * vect2 [0]);

      const double inv_norme = 1 / sqrt((perpendicular_vector [0] * perpendicular_vector [0]) + (perpendicular_vector [1] * perpendicular_vector [1]) + (perpendicular_vector [2] * perpendicular_vector [2]));
    
      perpendicular_vector [0] *= inv_norme;  
      perpendicular_vector [1] *= inv_norme;
      perpendicular_vector [2] *= inv_norme;


      scalar_product =  ( (perpendicular_vector [0] * vect3 [0]) + (perpendicular_vector [1] * vect3 [1]) + (perpendicular_vector [2] * vect3 [2]) ) ;

      if ( k < 0) k = -k;   
      if ( scalar_product < 0) k = -k;
      // TODO : il suffit de tester la valeur de mesh->face[f].normal_swap
	  // mais pour le moment cette routine n'est pas critique (suffisemment rapide)
	  
   
      // First virtual sphere
      /////////////////////////////////////////////   
      S.x = S1.x + k * perpendicular_vector [0];
      S.y = S1.y + k * perpendicular_vector [1];
      S.z = S1.z + k * perpendicular_vector [2];
      S.R = sphere_virtual_radius;
      S.type = VIRTUAL;
      S.tetraOwner = current_tetra_id;   
      
      added = false;
      for (unsigned int n = 0 ; n < j_ok.size() ; ++n) 
      {
        if (S.x == sphere[ j_ok[n] ].x && S.y == sphere[ j_ok[n] ].y && S.z == sphere[ j_ok[n] ].z) 
        {
          added = true;
          break;
        }
      }   
        
      if (!added) 
      {
        j_ok.push_back(sphereId);
        sphere.push_back(S); 
        partition.add(sphereId++,S.x,S.y,S.z);
      }
    
      // Second virtual sphere
      /////////////////////////////////////////////

      S.x = S2.x + k * perpendicular_vector [0];
      S.y = S2.y + k * perpendicular_vector [1];
      S.z = S2.z + k * perpendicular_vector [2];
      S.R = sphere_virtual_radius;
      S.type = VIRTUAL;
      S.tetraOwner = current_tetra_id;   
      
      added = false;
      for (unsigned int n = 0 ; n < j_ok.size() ; ++n) 
      {
        if (S.x == sphere[ j_ok[n] ].x && S.y == sphere[ j_ok[n] ].y && S.z == sphere[ j_ok[n] ].z) 
        {
          added = true;
          break;
        }
      }   
        
      if (!added) 
      {
        j_ok.push_back(sphereId);
        sphere.push_back(S); 
        partition.add(sphereId++,S.x,S.y,S.z);
      }
    
      // Third virtual sphere
      ///////////////////////////////////////////////   
      S.x = S3.x + k * perpendicular_vector [0];
      S.y = S3.y + k * perpendicular_vector [1];
      S.z = S3.z + k * perpendicular_vector [2];
      S.R = sphere_virtual_radius;
      S.type = VIRTUAL;
      S.tetraOwner = current_tetra_id;   
      
      added = false;
      for (unsigned int n = 0 ; n < j_ok.size() ; ++n) 
      {
        if (S.x == sphere[ j_ok[n] ].x && S.y == sphere[ j_ok[n] ].y && S.z == sphere[ j_ok[n] ].z) 
        {
          added = true;
          break;
        }
      }   
        
      if (!added) 
      {
        j_ok.push_back(sphereId);
        sphere.push_back(S); 
        partition.add(sphereId++,S.x,S.y,S.z);
      }
    
     // Fourth virtual sphere
      ///////////////////////////////////////////// 

      S.x = (S1.x + S2.x + S3.x) * div3 + k * perpendicular_vector [0];
      S.y = (S1.y + S2.y + S3.y) * div3 + k * perpendicular_vector [1];
      S.z = (S1.z + S2.z + S3.z) * div3 + k * perpendicular_vector [2];
      S.R = sphere_virtual_radius;

      S.type = VIRTUAL;
      S.tetraOwner = current_tetra_id;
      sphere.push_back(S);     
      partition.add(sphereId++,S.x,S.y,S.z);

      ///////////////////////////////////////////// 
    }

  }
  
  unsigned int id;
  Cell current_cell;
  double distance_max = -max_overlap_rate * rmin;

  for ( unsigned int n = 0 ; n < j_ok.size() ; ++n) //spheres virtuelles
  { 
    S = sphere[j_ok[n]];             
    partition.locateCellOf(S.x,S.y,S.z);

    for (unsigned int i = partition.i_down() ; i <= partition.i_up() ; ++i)
    {
      for (unsigned int j = partition.j_down() ; j <= partition.j_up() ; ++j)
      {
        for (unsigned int k = partition.k_down() ; k <= partition.k_up() ; ++k)
        {
          current_cell = partition.get_cell(i,j,k);
          for (unsigned int s = 0 ; s < current_cell.sphereId.size() ; ++s)
          {
            id = current_cell.sphereId[s];
            if (sphere[id].type != VIRTUAL && sphere[id].R > 0.0)
            {
              if ((distance_centre_spheres(S,sphere[id]) - (S.R + sphere[id].R)) < distance_max) sphere[id].R = 0.0; 
            }
          }
        
        }
      }
    }

  }
            
  END_FUNCTION;
  
}

void SpherePadder::insert_sphere(double x, double y, double z, double R)
{
  Sphere S;
  S.x = x;
  S.y = y;
  S.z = z;
  S.R = R;
  S.type = INSERTED_BY_USER;

  unsigned int inseredId = sphere.size();
  sphere.push_back(S);

  partition.locateCellOf(x-R, y-R, z-R);
  unsigned int iCellMin = partition.i_down();
  unsigned int jCellMin = partition.j_down();
  unsigned int kCellMin = partition.k_down();

  partition.locateCellOf(x+R, y+R, z+R);
  unsigned int iCellMax = partition.i_up();
  unsigned int jCellMax = partition.j_up();
  unsigned int kCellMax = partition.k_up();
  
  double distance_max = -max_overlap_rate * rmin;
  unsigned int id;
  Cell current_cell;

  for (unsigned int i = iCellMin ; i <= iCellMax ; ++i /*unsigned int i = 0 ; i <= partition.isize-1 ; ++i*/)
  {
	for (unsigned int j = jCellMin ; j <= jCellMax ; ++j /*unsigned int j = 0 ; j <= partition.jsize-1 ; ++j*/)
	{
	  for (unsigned int k = kCellMin ; k <= kCellMax ; ++k /*unsigned int k = 0 ; k <= partition.ksize-1 ; ++k*/)
	  {
		current_cell = partition.get_cell(i,j,k);
		partition.add_in_cell(inseredId,i,j,k); // FIXME could be set only in iCellMin+1 to iCellMax-1 ...
		for (unsigned int s = 0 ; s < current_cell.sphereId.size() ; ++s)
		{
		  id = current_cell.sphereId[s];
		  if (sphere[id].type != INSERTED_BY_USER && sphere[id].type != VIRTUAL && sphere[id].R > 0.0)
		  {
			if (distance_spheres(inseredId,id) < distance_max)
			{
			  sphere[id].R = 0.0;
			}
		  }
		}
	  }
	}
  }


//   for (/*unsigned int i = iCellMin ; i <= iCellMax ; ++i*/unsigned int i = 0 ; i <= partition.isize-1 ; ++i)
//   {
// 	for (/*unsigned int j = jCellMin ; j <= jCellMax ; ++j*/unsigned int j = 0 ; j <= partition.jsize-1 ; ++j)
// 	{
// 	  for (/*unsigned int k = kCellMin ; k <= kCellMax ; ++k*/unsigned int k = 0 ; k <= partition.ksize-1 ; ++k)
// 	  {
// 	
// 		current_cell = partition.get_cell(i,j,k);
// 		for (unsigned int s = 0 ; s < current_cell.sphereId.size() ; ++s)
// 		{
// 
// 		  if (current_cell.sphereId[s] == inseredId)
// 			cout << "Cell " << i << ", " << j << ", " << k << "   OK    -> " << current_cell.sphereId[s] << endl;
// 
// 		}
// 	  }
// 	}
//   }



  
}

void SpherePadder::cancel_overlaps()
{
  BEGIN_FUNCTION("Cancel_overlaps");

  double distance;
  double distance_max = -max_overlap_rate * rmin; 
  unsigned int id;
  Cell current_cell;
  double kfact;
  
  for(unsigned int sphereId = 0 ; sphereId <  sphere.size() ; ++(sphereId))
  {
    
    partition.locateCellOf(sphere[sphereId].x,sphere[sphereId].y,sphere[sphereId].z);
    
    for (unsigned int i = partition.i_down() ; i <= partition.i_up() ; ++i)
    {
      for (unsigned int j = partition.j_down() ; j <= partition.j_up() ; ++j)
      {
        for (unsigned int k = partition.k_down() ; k <= partition.k_up() ; ++k)
        {
          current_cell = partition.get_cell(i,j,k);
          for (unsigned int s = 0 ; s < current_cell.sphereId.size() ; ++s)
          {
            id = current_cell.sphereId[s];
            if (id != sphereId && sphere[id].R > 0.0)
            {
			  // Virtual spheres and spheres added by user cannot be modified here
// 			  unsigned int opt = 0x00;
// 			  if (sphere[sphereId].type == VIRTUAL || sphere[sphereId].type == INSERTED_BY_USER) opt |= 0x01;
// 			  if (sphere[id].type == VIRTUAL || sphere[id].type == INSERTED_BY_USER) opt |= 0x02;
// 			  if (opt == 0x03) continue;
			  double inv_sumR = 1.0 / (sphere[sphereId].R + sphere[id].R);
              while ( (distance = distance_spheres(sphereId,id)) < distance_max )
              {                                               
                kfact = 1.0 + distance * inv_sumR;
                //if (opt | 0x01) // test a revoir
				  sphere[sphereId].R *= kfact;
				//if (opt | 0x02)
				  sphere[id].R       *= kfact;
              }
			  
			  if (sphere[id].R < rmin) sphere[id].R = 0.0;
			  if (sphere[sphereId].R < rmin) sphere[sphereId].R = 0.0;
            }
          }
        }
      }
    }
     
  }
  
  END_FUNCTION;
}


void SpherePadder::detect_overlap ()
{
  BEGIN_FUNCTION("Detect overlap");
  Sphere S1,S2;
  unsigned int nb_overlap = 0;
  double d;
  
  for (unsigned int n = 0 ; n < sphere.size()-1 ; ++n)
  {
    S1 = sphere[ n ];
    if ( S1.type != VIRTUAL && S1.R > rmin )
    {
      for (unsigned int t = n+1 ; t < sphere.size() ; ++t)
      {
        S2 = sphere[ t ];
        if ( S2.type != VIRTUAL && S2.R > rmin)
        {
          d = distance_spheres(n, t);
          
          if (d < -max_overlap_rate * rmin)
          {
            cerr << "Overlap!" << endl;
            partition.locateCellOf(S1.x,S1.y,S1.z);
			cerr << "  Spheres         = " << n << ", " << t << endl;
            cerr << "  Cell ijk (S1)   = " << partition.current_i << ", " << partition.current_j << ", " << partition.current_k << endl;
            partition.locateCellOf(S2.x,S2.y,S2.z);
            cerr << "  Cell ijk (S2)   = " << partition.current_i << ", " << partition.current_j << ", " << partition.current_k << endl;
            cerr << "  Types           = " << S1.type << ", " << S2.type << endl;
            cerr << "  Radii           = " << S1.R << ", " << S2.R << endl;
            cerr << "  pos S1          = " << S1.x << ", " << S1.y << ", " << S1.z << endl;
            cerr << "  pos S2          = " << S2.x << ", " << S2.y << ", " << S2.z << endl;
            cerr << "  Distance / rmin = " << d/rmin << endl;
            //cerr << "  rmin            = " << rmin << endl;
            //sphere[n].type = sphere[t].type = AT_TETRA_VERTEX;
            //sphere[n].R = sphere[t].R = 0.0;
            ++(nb_overlap);
          }
        }
      }
    }
  }
  cerr << "NB Overlap = " << nb_overlap << endl;
  
  END_FUNCTION; 
}        


double SpherePadder::solid_volume_of_tetrahedron(Sphere& S1, Sphere& S2, Sphere& S3, Sphere& S4)
{
  double volume_portion1;
  double volume_portion2;
  double volume_portion3;
  double volume_portion4;
  
  double point1[4];
  point1[0] = S1.x;
  point1[1] = S1.y;
  point1[2] = S1.z;
  point1[3] = S1.R;
  
  double point2[4];
  point2[0] = S2.x;
  point2[1] = S2.y;
  point2[2] = S2.z;
  point2[3] = S2.R;

  double point3[4];
  point3[0] = S3.x;
  point3[1] = S3.y;
  point3[2] = S3.z;
  point3[3] = S3.R;
  
  double point4[4];
  point4[0] = S4.x;
  point4[1] = S4.y;
  point4[2] = S4.z;
  point4[3] = S4.R;
  
  volume_portion1 = spherical_triangle(point1, point2, point3, point4);
  volume_portion2 = spherical_triangle(point2, point1, point3, point4);
  volume_portion3 = spherical_triangle(point3, point1, point2, point4);
  volume_portion4 = spherical_triangle(point4, point1, point2, point3);

  return (volume_portion1 + volume_portion2 + volume_portion3 + volume_portion4);
}

// point : x,y,z,R
double SpherePadder::spherical_triangle (double point1[],double point2[],double point3[],double point4[])
{

  double rayon = point1[3];
  if (rayon == 0.0) return 0.0;
  
  double vect12[3], vect13[3], vect14[3];

  vect12[0] = point2[0] - point1[0];
  vect12[1] = point2[1] - point1[1];
  vect12[2] = point2[2] - point1[2];

  vect13[0] = point3[0] - point1[0];
  vect13[1] = point3[1] - point1[1];
  vect13[2] = point3[2] - point1[2];

  vect14[0] = point4[0] - point1[0];
  vect14[1] = point4[1] - point1[1];
  vect14[2] = point4[2] - point1[2];

  double norme12 = sqrt( (vect12[0]*vect12[0]) + (vect12[1]*vect12[1]) + (vect12[2]*vect12[2]) ); 
  double norme13 = sqrt( (vect13[0]*vect13[0]) + (vect13[1]*vect13[1]) + (vect13[2]*vect13[2]) ); 
  double norme14 = sqrt( (vect14[0]*vect14[0]) + (vect14[1]*vect14[1]) + (vect14[2]*vect14[2]) ); 
  
  double A = acos( (vect12[0]*vect13[0] + vect12[1]*vect13[1] + vect12[2]*vect13[2]) / (norme13 * norme12));
  double B = acos( (vect12[0]*vect14[0] + vect12[1]*vect14[1] + vect12[2]*vect14[2]) / (norme14 * norme12));
  double C = acos( (vect14[0]*vect13[0] + vect14[1]*vect13[1] + vect14[2]*vect13[2]) / (norme13 * norme14));

  double a = acos( (cos(A) - cos(B) * cos(C)) / (sin(B) * sin(C)) );
  double b = acos( (cos(B) - cos(C) * cos(A)) / (sin(C) * sin(A)) );
  double c = acos( (cos(C) - cos(A) * cos(B)) / (sin(A) * sin(B)) );
  
  double aire_triangle_spherique = rayon * rayon * (a + b + c - M_PI);

  double aire_sphere = 4.0 * M_PI * rayon * rayon;

  return ( (4.0 * 0.3333333 * M_PI * rayon * rayon * rayon) * (aire_triangle_spherique / aire_sphere) ) ;

}

// ============================
//           ANALISYS
// ============================

void SpherePadder::check_inProbe(unsigned int i)
{
  if (!probeIsDefined)    return;
  if (sphere[i].R <= 0.0) return;
  
  double dx = sphere[i].x - xProbe;
  double dy = sphere[i].y - yProbe;
  double dz = sphere[i].z - zProbe;
  double squared_distance = dx*dx + dy*dy + dz*dz;
  if (squared_distance + sphere[i].R*sphere[i].R < RProbe * RProbe) sphereInProbe.push_back(i);
}

void SpherePadder::add_spherical_probe(double Rfact)
{
  double xmin,xmax;
  double ymin,ymax;
  double zmin,zmax;
  double R;
  
  xmin=xmax=mesh->node[0].x;
  ymin=ymax=mesh->node[0].y;
  zmin=zmax=mesh->node[0].z;
  for (unsigned int i = 1 ; i < mesh->node.size() ; ++i)
  {
	xmin = (xmin > mesh->node[i].x) ? mesh->node[i].x : xmin;
	xmax = (xmax < mesh->node[i].x) ? mesh->node[i].x : xmax;
	ymin = (ymin > mesh->node[i].y) ? mesh->node[i].y : ymin;
	ymax = (ymax < mesh->node[i].y) ? mesh->node[i].y : ymax;
	zmin = (zmin > mesh->node[i].z) ? mesh->node[i].z : zmin;
	zmax = (zmax < mesh->node[i].z) ? mesh->node[i].z : zmax;
  }
  xProbe = 0.5 * (xmin + xmax);
  yProbe = 0.5 * (ymin + ymax);
  zProbe = 0.5 * (zmin + zmax);
  RProbe = (xmax - xmin);
  RProbe = (RProbe < (R = ymax - ymin)) ? RProbe : R;
  RProbe = (RProbe < (R = zmax - zmin)) ? RProbe : R;
  RProbe *= 0.5 * Rfact;
  probeIsDefined = true;
  compacity_file.open("compacity.dat");
}

double SpherePadder::compacity_in_probe(unsigned int ninsered)
{
  if (!probeIsDefined) return -1.0;
  
  double dr = 0.0;
  double Vs = 0.0;
  double fact = 1.333333333 * M_PI;
  for (unsigned int i = 1 ; i < sphereInProbe.size() ; ++i)
  {
	Vs += fact * sphere[i].R * sphere[i].R * sphere[i].R;
  }
  
  // TODO ameliorer cette fonction en prennant en compte les spheres coupees...
  
  dr = Vs / (fact*RProbe*RProbe*RProbe);
  compacity_file << ninsered << ' ' << dr << endl;
  return (dr);
}





