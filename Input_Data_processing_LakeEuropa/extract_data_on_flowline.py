# -*- coding: utf-8 -*-
"""
Created on Wed Nov  9 16:17:38 2022

@author: trunzc
"""

#extract data on flow line path
from astropy.io import fits
from astropy.utils.data import get_pkg_data_filename
from astropy.convolution import Gaussian2DKernel, interpolate_replace_nans
from osgeo import gdal,ogr
from matplotlib import pyplot as plt
import matplotlib.cm as cm
#import matplotlib.cm as cm
import numpy as np
import netCDF4 as nc
import seaborn as sns
import pandas as pd
#from math import radians, cos, sin, asin, sqrt
#from scipy.spatial import KDTree
from scipy.interpolate import RectBivariateSpline    # interpolate grid data to point coordinates
#from scipy.interpolate import interp1d


def get_xy_array_geotiff(rds):
    """
    Gets the easting and northing of the geotiff. 
    Code comes from Christian Wild (Oregon State University)

    Parameters
    ----------
    rds : gdal.Dataset
        Geotiff loaded with gdal.Open('geotiff.tif').

    Returns
    -------
    easting : Array of float64
        x coordinates of the grid (pixel centered).
    northing : Array of float64
        y coordinates of the grid (pixel centered).

    """

    # get some more info about the grid
    nx = rds.RasterXSize
    ny = rds.RasterYSize

    geotransform = rds.GetGeoTransform()
    originX = geotransform[0]
    originY = geotransform[3]
    pixelWidth = geotransform[1]
    pixelHeight = geotransform[5]
    
    endX = originX + pixelWidth * nx
    endY = originY + pixelHeight * ny
    
    easting = np.arange(nx) * pixelWidth + originX + pixelWidth/2.0 # pixel center
    northing = np.arange(ny) * pixelHeight + originY + pixelHeight/2.0 # pixel center
    
    #grid_lons, grid_lats = np.meshgrid(lons, lats)
    return easting,northing

def get_geotiff_data(path_to_geotiff,interpolation_iteration=4):  
    rds = gdal.Open(path_to_geotiff)
    band = rds.GetRasterBand(1)
    data = {}  
    data['grid'] = band.ReadAsArray()
    data['grid'][data['grid']==-9999]=np.nan
    data['easting'],data['northing']=get_xy_array_geotiff(rds)
    
    #interpolate nans
    # We smooth with a Gaussian kernel with x_stddev=1 (and y_stddev=1)
    # It is a 9x9 array
    kernel = Gaussian2DKernel(x_stddev=1)
    # create a "fixed" image with NaNs replaced by interpolated values
    for i in np.arange(interpolation_iteration):
        
        data['grid_interpolated'] = interpolate_replace_nans(data['grid'], kernel)
    data['grid_interpolated'] [np.isnan(data['grid_interpolated'] )] = -9999
    #data['grid_interpolated'] = np.nan_to_num(data['grid_interpolated'], nan=-9999)

    return data

def get_netcdf_data(netcdf_file_path, data_type='Measures'): #

    #load netcdf data
    ds = nc.Dataset(netcdf_file_path)
    #display all the variables stored in the netcdf file
    print(ds.variables.keys())       
    data = {}
    
    if data_type == 'Promice':  
        
        #Velocity netcdf file from 
        #Solgaard, A. et al. Greenland ice velocity maps from the PROMICE project. Earth System Science Data 13, 3491???3512 (2021).
        #Downloaded in the Dataverse on this page: https://dataverse.geus.dk/dataverse/Ice_velocity/
        #"Multi-year Ice Velocity Mosaics for the Greenland Ice Sheet from Sentinel-1 Edition 1"
        #velocities are in  m/day
    
        #% extract x and y velocites arrays from netcdf   
        data['velocity_easting'] = ds['land_ice_surface_easting_velocity'][:][0]
        data['velocity_northing'] = ds['land_ice_surface_northing_velocity'][:][0]
        data['velocity_magnitude'] = ds['land_ice_surface_velocity_magnitude'][:][0]
        data['easting'] = ds['x'][:]
        data['northing'] = ds['y'][:]
        
    if data_type == 'Measures':
        #Velocity netcdf file from 
        #https://its-live.jpl.nasa.gov/
        
        # velocities are in meter per year
        # projection system: "WGS 84 / NSIDC Sea Ice Polar Stereographic North"
        
        #% extract x and y velocites arrays from netcdf   
        data['velocity_easting'] = ds['vx'][:]
        data['velocity_northing'] = ds['vy'][:]
        data['velocity_magnitude'] = ds['v'][:]
        data['easting'] = ds['x'][:]
        data['northing'] = ds['y'][:]   
        
    
    #% extract arrays from netcdf       
    if data_type == 'Bedmachine':  
        data['surface'] = ds['surface'][:]
        data['thickness'] = ds['thickness'][:]
        data['bed'] = ds['bed'][:]
        data['easting'] = ds['x'][:]
        data['northing'] = ds['y'][:]   
          
    return data

# def get_data_from_profile(flowline, data, layer_name, plot=False):
#     rbs_surface = RectBivariateSpline(data['easting'], data['northing'][::-1], data[layer_name][::-1].T)
    
#     profile = rbs_surface.ev(flowline.easting, flowline.northing)
#     if plot==True:
#         fig,ax = plt.subplots()
#         ax.plot(flowline.distance,profile_ice_surface)
#     return profile




def get_data_from_profile(flowline, data, layer_name):
    
    rbs_surface = RectBivariateSpline(data['easting'], data['northing'][::-1], data[layer_name][::-1].T) 
    profile = rbs_surface.ev(flowline.easting, flowline.northing)
    return profile


def plot_map(fig, ax, 
             grid=[],
             easting=[],
             northing=[],
             xlim=[-560000,-490000],
             ylim=[-1260000,-1180000],
             vlim=None):
    
   # fig, ax = plt.subplots()
    extent=[easting[0], easting[-1],northing[-1], northing[0]]
    #years = range(len(flowline['velocity_easting']))
    
    #plot velocity map 
    if vlim==None:
        sc = ax.imshow(grid,extent=extent)
    else:
        sc = ax.imshow(grid,extent=extent,vmin=vlim[0],vmax=vlim[1])
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    bar = plt.colorbar(sc)
    
    
def plot_flowline(fig, ax,profile):
    years = range(len(profile))
    sc = ax.scatter(profile['easting'],profile['northing'],c=years,cmap=cm.jet)
    cbar = plt.colorbar(sc, ax=ax)
    cbar.set_label('years')
    


def find_extent_on_profile(extent_lower_left_corner, extent_upper_right_corner):
    area = profile.distance[(profile.easting > extent_lower_left_corner[0]) & 
                                 (profile.easting < extent_upper_right_corner[0]) & 
                                 (profile.northing > extent_lower_left_corner[1]) & 
                                 (profile.northing < extent_upper_right_corner[1]) ]
    
    return area.reset_index(drop=True)

#%%



# Load flowline
# profile = pd.read_csv('G:/Shared drives/6 Greenland Europa Hiawatha Projects/Lake Europa/FlowBand/Flowlines/promice_500m_europa_flowline_camp.csv', 
#                        index_col=0)

# profile = pd.read_csv('G:/Shared drives/6 Greenland Europa Hiawatha Projects/Lake Europa/FlowBand/Flowlines/promice_500m_europa_flowline_2.csv', 
#                        index_col=0)

profile = pd.read_csv('G:/Shared drives/6 Greenland Europa Hiawatha Projects/Lake Europa/FlowBand/Flowlines/promice_500m_europa_flowline_camp.csv', 
                        index_col=0)

lake_extent_sw = [-521139.211,-1194232.358]
lake_extent_ne = [-514887.923,-1190764.258]

radar_extent_sw = [-522520.647,-1194383.272]
radar_extent_ne = [-512374.638,-1190389.877]    
lake_area = find_extent_on_profile(lake_extent_sw, lake_extent_ne)    

radar_area = find_extent_on_profile(radar_extent_sw, radar_extent_ne)   
    
#!! make this a function

#Load data from tiffs and netcdf

ramco_temperature = get_geotiff_data('J:/QGreenland_v2.0.0/Regional climate models/RACMO model output/Annual mean temperature at 2m 1958-2019 (1km)/racmo_t2m.tif')
ramco_precipitation = get_geotiff_data('J:/QGreenland_v2.0.0/Regional climate models/RACMO model output/Total precipitation 1958-2019 (1km)/racmo_precip.tif')
ramco_runoff = get_geotiff_data('J:/QGreenland_v2.0.0/Regional climate models/RACMO model output/Runoff 1958-2019 (1km)/racmo_runoff.tif')
ramco_melt = get_geotiff_data('J:/QGreenland_v2.0.0/Regional climate models/RACMO model output/Snowmelt 1958-2019 (1km)/racmo_snowmelt.tif')
ramco_sublimation = get_geotiff_data('J:/QGreenland_v2.0.0/Regional climate models/RACMO model output/Sublimation 1958-2019 (1km)/racmo_subl.tif')

bedmachine = get_netcdf_data('J:/QGreenland_v2.0.0/Additional/BedMachineGreenland_V5/BedMachineGreenland-v5.nc', 
                             data_type='Bedmachine')

#arcticdem_2m = get_geotiff_data('J:/QGreenland_v2.0.0/Additional/Arctic DEM/Arctic_DEM_mosaic_merged_2m.tif')
arcticdem_10m = get_geotiff_data('J:/QGreenland_v2.0.0/Additional/Arctic DEM/Arctic_DEM_mosaic_merged_10m.tif')
arcticdem_32m = get_geotiff_data('J:/QGreenland_v2.0.0/Additional/Arctic DEM/Arctic_DEM_mosaic_merged_32m.tif')

promice_velocity = get_netcdf_data('J:/QGreenland_v2.0.0/Additional/PROMICE Multi-year ice velocity/Promice_AVG5year.nc',
                               data_type='Promice')
#measures_velocity = get_netcdf_data('J:/QGreenland_v2.0.0/Additional/MEaSUREs 120m composite velocity/GRE_G0120_0000.nc', 
#                                data_type='Measures')



#extract profiles
profile['ramco_2m_air_temperature_kelvin'] = get_data_from_profile(profile, ramco_temperature, 'grid_interpolated')
profile['ramco_total_precipitation_mm_water_equivalent']  = get_data_from_profile(profile, ramco_precipitation, 'grid_interpolated')
profile['ramco_runoff_mm_water_equivalent']  = get_data_from_profile(profile, ramco_runoff, 'grid_interpolated')
profile['ramco_snowmelt_mm_water_equivalent']  = get_data_from_profile(profile, ramco_melt, 'grid_interpolated')
profile['ramco_sublimation_mm_water_equivalent']  = get_data_from_profile(profile, ramco_sublimation, 'grid_interpolated')
#profile['total_melt']
profile['bedmachine_ice_surface_elevation_masl']  = get_data_from_profile(profile, bedmachine, 'surface')
profile['bedmachine_ice_thickness_m']  = get_data_from_profile(profile, bedmachine, 'thickness')
profile['bedmachine_bed_elevation_masl']  = get_data_from_profile(profile, bedmachine, 'bed')

#profile['arcticdem_2m_ice_surface_elevation_masl']  = get_data_from_profile(profile, arcticdem_2m, 'grid_interpolated')
profile['arcticdem_10m_ice_surface_elevation_masl']  = get_data_from_profile(profile, arcticdem_10m, 'grid_interpolated')
profile['arcticdem_32m_ice_surface_elevation_masl']  = get_data_from_profile(profile, arcticdem_32m, 'grid_interpolated')

profile['promice_velocity_mperday']  = get_data_from_profile(profile, promice_velocity, 'velocity_magnitude')

#this calculation is based of Kiya and Georgia. its missing drift erosion
profile['ramco_total_mass_loss'] = profile['ramco_runoff_mm_water_equivalent']-profile['ramco_sublimation_mm_water_equivalent']
# for christian's model
profile['ramco_mass_balance'] = profile['ramco_total_precipitation_mm_water_equivalent'] - profile['ramco_total_mass_loss']

profile.to_csv('profile_data_lake_europa.csv')
#%%

fig,(ax1,ax2,ax3,ax4, ax5) = plt.subplots(5, sharex=True)

ax1.plot(profile.distance,profile.ramco_2m_air_temperature_kelvin, label='Air temp')

ax2.plot(profile.distance,profile.ramco_total_precipitation_mm_water_equivalent, label='Precipitation - RACMO')
ax2.plot(profile.distance,profile.ramco_runoff_mm_water_equivalent, label='Runoff - RACMO')
ax2.plot(profile.distance,profile.ramco_snowmelt_mm_water_equivalent, label='Snow melt - RACMO')
ax2.plot(profile.distance,profile.ramco_sublimation_mm_water_equivalent, label='Sublimation - RACMO')

ax3.plot(profile.distance,profile.bedmachine_ice_thickness_m, label='Ice thickness - Bedmachine v5')

ax4.fill_between(profile.distance, profile.bedmachine_ice_surface_elevation_masl, profile.bedmachine_bed_elevation_masl, alpha=0.3)
ax4.plot(profile.distance,profile.bedmachine_ice_surface_elevation_masl, label='Ice elevation - Bedmachine v5')
ax4.plot(profile.distance,profile.bedmachine_bed_elevation_masl, label='Bed elevation - Bedmachine v5')

ax5.plot(profile.distance,profile.promice_velocity_mperday*365, label='Mean surface velocity - Promice')

ax1.axvspan(lake_area[0],lake_area[len(lake_area)-1], alpha=0.3, color='cyan', label='minimum lake extent')
ax1.axvspan(radar_area[0],radar_area[len(radar_area)-1], alpha=0.3, color='grey', label='radar extent')

ax2.axvspan(lake_area[0],lake_area[len(lake_area)-1], alpha=0.3, color='cyan')
ax2.axvspan(radar_area[0],radar_area[len(radar_area)-1], alpha=0.3, color='grey')

ax3.axvspan(lake_area[0],lake_area[len(lake_area)-1], alpha=0.3, color='cyan')
ax3.axvspan(radar_area[0],radar_area[len(radar_area)-1], alpha=0.3, color='grey')

ax4.axvspan(lake_area[0],lake_area[len(lake_area)-1], alpha=0.3, color='cyan')
ax4.axvspan(radar_area[0],radar_area[len(radar_area)-1], alpha=0.3, color='grey')

ax5.axvspan(lake_area[0],lake_area[len(lake_area)-1], alpha=0.3, color='cyan')
ax5.axvspan(radar_area[0],radar_area[len(radar_area)-1], alpha=0.3, color='grey')

ax1.legend()
ax2.legend()
ax3.legend()
ax4.legend()
ax5.legend()


ax1.set_ylabel('(k)')
ax2.set_ylabel('(mm w.e.)')
ax3.set_ylabel('(m)')
ax4.set_ylabel('(m.a.s.l.)')
ax5.set_ylabel('(m/year)')

#%%

#select extent
# xlim=[-560000,-490000]
# ylim=[-1260000,-1180000]
# index_easting = np.where((ramco_melt['easting'] > xlim[0]) & (ramco_melt['easting'] < xlim[1]))
# index_northing = np.where((ramco_melt['northing'] > ylim[0]) & (ramco_melt['northing'] < ylim[1]))


camp = [-516335.771, -1191434.196]


xlim = [-560000,-490000]
ylim = [-1260000,-1180000]

fig,ax = plt.subplots()
plot_map(fig, ax,
         grid = ramco_temperature['grid_interpolated'],
         easting = ramco_temperature['easting'],
         northing = ramco_temperature['northing'],
         xlim = xlim,
         ylim = ylim,
         vlim=[250,260])
plot_flowline(fig,ax, profile)
plt.title('temperature')

ax.plot(camp[0],camp[1],marker='x',markersize=12,color='black')

fig,ax = plt.subplots()
plot_map(fig, ax,
         grid = ramco_precipitation['grid_interpolated'],
         easting = ramco_precipitation['easting'],
         northing = ramco_precipitation['northing'],
         xlim = xlim,
         ylim = ylim,
         vlim=[0,750])
plot_flowline(fig,ax, profile)
plt.title('precipitation')

ax.plot(camp[0],camp[1],marker='x',markersize=12,color='black')

fig,ax = plt.subplots()
plot_map(fig, ax,
         grid = ramco_runoff['grid_interpolated'],
         easting = ramco_runoff['easting'],
         northing = ramco_runoff['northing'],
         xlim = xlim,
         ylim = ylim,
         vlim=[0,750])
plot_flowline(fig,ax, profile)
plt.title('runoff')

ax.plot(camp[0],camp[1],marker='x',markersize=12,color='black')

fig,ax = plt.subplots()
plot_map(fig, ax,
         grid = ramco_melt['grid_interpolated'],
         easting = ramco_melt['easting'],
         northing = ramco_melt['northing'],
         xlim = xlim,
         ylim = ylim,
         vlim=[0,750])
plot_flowline(fig,ax, profile)
plt.title('melt')

fig,ax = plt.subplots()
plot_map(fig, ax,
         grid = ramco_sublimation['grid_interpolated'],
         easting = ramco_sublimation['easting'],
         northing = ramco_sublimation['northing'],
         xlim = xlim,
         ylim = ylim,
         vlim=[0,750])
plot_flowline(fig,ax, profile)
plt.title('sublimation')

ax.plot(camp[0],camp[1],marker='x',markersize=12,color='black')

#%%

# rbs_surface = RectBivariateSpline(ramco_temperature['easting'], ramco_temperature['northing'][::-1], ramco_temperature['grid_interpolated'][::-1].T)

# test = rbs_surface.ev(profile.easting, profile.northing)

# fig,ax = plt.subplots()
# ax.plot(profile.distance,test)

    
    
    
    
    
    
    
