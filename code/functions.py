#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import os
import pandas as pd
import json
import requests
import fiona
from shapely.geometry import shape, mapping, Point, Polygon, MultiPolygon
import pyproj
import math
import threading                                                                


# In[ ]:


def distance(point1, point2):
    return ((point1[0]-point2[0])**2+(point1[1]-point2[1])**2)**0.5


# In[ ]:


def getSDOs(df):
    SDOs = list(df.SDO_ID.unique())
    SDOs.sort()
    return SDOs


# In[ ]:


def getPointBySDO_ID(df, SDO_ID):
    res = df[df['SDO_ID']==SDO_ID]
    point = tuple(res["loc"].to_list())
    return point[0]


# In[ ]:


def getSDODF():
    WinddatenSDO = "../data/Winddaten/data/sdo.csv"
    df = pd.read_csv(WinddatenSDO)
    df["loc"] = df.Geogr_Breite + ", " + df.Geogr_Laenge
    a = df["loc"].to_list()
    b = []
    for x, y in [x.split(", ") for x in a]:
        b.append((float((x.replace(",", "."))), float((y.replace(",", ".")))))
    df["loc"] = b
    return df


# In[ ]:


def getWindDF():
    Winddaten = "../data/Winddaten/data/data.csv"
    df = pd.read_csv(Winddaten, sep=',')
    df.columns = ["SDO_ID", "Zeitstempel", "Wert", "Qualitaet_Byte", "Qualitaet_Niveau", "sth."]
    return df


# In[ ]:


def loadWindBySDO_ID(dfWind, SDO_ID):
    gf = dfWind.groupby("SDO_ID")
    #print("Winddurchschnitt von", dfWind.Zeitstempel.min(), "bis", dfWind.Zeitstempel.max())
    return gf.get_group(SDO_ID).Wert.mean()


# In[ ]:


def getDistancesAndWind(point):
    dfWind = getWindDF()
    dfSDO = getSDODF()
    SDOs = getSDOs(dfWind)
    #print(len(SDOs))
    a = {}
    for SDO_ID in SDOs:
        SDOPoint = getPointBySDO_ID(dfSDO, SDO_ID)
        d = distance(point, SDOPoint)
        w = loadWindBySDO_ID(dfWind, SDO_ID)
        a[SDO_ID] = [d, w]
    return a


# In[ ]:


def getBenachbarteTags(point):
    x, y = point
    #benachbarte Objekte
    data = f"data=%5Btimeout%3A10%5D%5Bout%3Ajson%5D%3B(node(around%3A50%2C{x}%2C{y})%3Bway(around%3A50%2C{x}%2C{y})%3B)%3Bout+tags+geom({x-0.0057}%2C{y-0.0057}%2C{x+0.0057}%2C{y+0.0057})%3Brelation(around%3A50%2C{x}%2C{y})%3Bout+geom({x-0.0057}%2C{y-0.0057}%2C{x+0.0057}%2C{y+0.0057})%3B"
    response = requests.post('https://query.openstreetmap.org/query-features', data=data)
    try:
        res = json.loads(response.text)
        features = {}
        #return res
        for entry in res["elements"]:
            a = entry.get("tags")
            if a:
                for key, value in a.items():
                    features.update({key:value})
    except:
        return None
    return json.dumps(features)


# In[ ]:


def getUnmschlie??endeTags(point):
    x, y = point
    #unmschlie??endes Objekte
    data = f"data=%5Btimeout%3A10%5D%5Bout%3Ajson%5D%3Bis_in({x}%2C{y})-%3E.a%3Bway(pivot.a)%3Bout+tags+bb%3Bout+ids+geom({x}%2C{y}%2C{x}%2C{y})%3Brelation(pivot.a)%3Bout+tags+bb%3B"
    response = requests.post('https://query.openstreetmap.org/query-features', data=data)
    try:
        res = json.loads(response.text)
        features = {}
        #return res
        for entry in res["elements"]:
            a = entry.get("tags")
            if a:
                for key, value in a.items():
                    features.update({key:value})
    except:
        return None 
    return json.dumps(features)


# In[ ]:


P = pyproj.Proj(proj='utm', zone=31, ellps='WGS84', preserve_units=True)
G = pyproj.Geod(ellps='WGS84')

def LatLon_To_XY(Lat,Lon):
    return P(Lat,Lon)

def XY_To_LatLon(x,y):
    return P(x,y,inverse=True)   


# In[ ]:


def PointInPoly(point, geojsonPath):
    multipol = fiona.open(geojsonPath)
    for multi in multipol:
        if Point(point).within(shape(multi['geometry'])):
            return True
    return False 


# In[ ]:


def PointInSchutzgebiet(a):
    point = LatLon_To_XY(a[1], a[0])
    path = "../data/Schutzgebiete/"
    files = ["../data/Schutzgebiete/"+f for f in os.listdir(path) if f[-4:]=="json"]
    res = [i for i in range(len(files))]
    for i, geojsonPath in enumerate(files):
        #print(f"Scanning {geojsonPath}")
        if PointInPoly(point, geojsonPath):
            res[i]=1
        else:
            res[i]=0
    return res      


# In[ ]:


def getWinkraftPoints():
    df = pd.read_csv("../prep_data/Windkraftanlagen.csv")
    a = [x.split(", ") for x in df["loc"].to_list()]
    b= []
    for x,y in a:
        b.append([float(x), float(y)])
    WinkraftPoints = [tuple(x) for x in b]
    return WinkraftPoints


# In[ ]:


def getNoWindkraftPoints():
    df = pd.read_csv("NoWindkraftanlagen.csv")
    points = []
    for item in df["loc"].to_list():
        x, y = item[1:-1].split(", ")
        points.append((float(x), float(y)))
    return points


# # WindkraftPoints

# In[ ]:


WinkraftPoints = getWinkraftPoints()


# In[ ]:


#Naturmonumente, Nationalparke, Vogelschutzgebiet, Landschaftsschutzgebiete, Naturschutzgebiete, Biosphaerenreservate
#columns = ["Naturmonumente", "Nationalparke", "Vogelschutzgebiet", "Landschaftsschutzgebiete", "Naturschutzgebiete", "Biosphaerenreservate"]

#inSchutzGebiet = []
#for point in WinkraftPoints:
#    inSchutzGebiet.append(PointInSchutzgebiet(point))


# In[ ]:


umschlie??endeTags = []
benachbarteTags = []
distanceAndWind = []

for point in WinkraftPoints:
    umschlie??endeTags.append(getUnmschlie??endeTags(point))
    benachbarteTags.append(getBenachbarteTags(point))     
    distanceAndWind.append(getDistancesAndWind(point))
    print("Done")


# In[ ]:


df = pd.DataFrame()
df["loc"] = WinkraftPoints
#df["schutzgebiete"] = inSchutzGebiet
df["umschlie??endeTags"] = umschlie??endeTags
df["benachbarteTags"] = benachbarteTags
df["distanceAndWind"] = distanceAndWind
df.to_csv("prepWindKraft.csv", index=False)
df["Label"] = [True for x in range(len(df))]
df.to_csv("prepWindKraftLabel.csv", index=False)


# # NO WindkraftPoints

# In[ ]:


NoWinkraftPoints = getNoWindkraftPoints()#[:10]

#Naturmonumente, Nationalparke, Vogelschutzgebiet, Landschaftsschutzgebiete, Naturschutzgebiete, Biosphaerenreservate
#columns = ["Naturmonumente", "Nationalparke", "Vogelschutzgebiet", "Landschaftsschutzgebiete", "Naturschutzgebiete", "Biosphaerenreservate"]

#inSchutzGebiet1 = []
#for point in NoWinkraftPoints:
#    inSchutzGebiet1.append(PointInSchutzgebiet(point))
    
umschlie??endeTags1 = []
benachbarteTags1 = []
distanceAndWind1 = []

for point in NoWinkraftPoints:
    distanceAndWind1.append(getDistancesAndWind(point))
    umschlie??endeTags1.append(getUnmschlie??endeTags(point))
    benachbarteTags1.append(getBenachbarteTags(point))
    print("Done")


# In[ ]:


df1 = pd.DataFrame()
df1["loc"] = NoWinkraftPoints
#df1["schutzgebiete"] = inSchutzGebiet1
df1["umschlie??endeTags"] = umschlie??endeTags1
df1["benachbarteTags"] = benachbarteTags1
df1["distanceAndWind"] = distanceAndWind1
df1.to_csv("prepNoWindKraft.csv", index=False)
df1["Label"] = [False for x in range(len(df1))]
df1.to_csv("prepNoWindKraftLabel.csv", index=False)

