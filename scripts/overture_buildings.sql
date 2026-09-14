-- Overture Buildings, CMAP bbox, DuckDB. Run on the workstation, not CI.
-- https://docs.overturemaps.org/getting-data/

INSTALL httpfs; LOAD httpfs;
INSTALL spatial; LOAD spatial;

-- Point this at a release you actually downloaded, or httpfs a public parquet.
-- Clip first. The planet buildings theme will melt a 10 GB card and a laptop SSD.

CREATE TABLE naperville_bldg AS
SELECT
  id,
  height,
  ST_GeomFromWKB(geometry) AS geom
FROM read_parquet('overture/buildings/*.parquet')
WHERE bbox.xmin > -88.71 AND bbox.xmax < -87.02
  AND bbox.ymin > 41.20 AND bbox.ymax < 42.50;

COPY naperville_bldg TO 'data/processed/overture_buildings.parquet';
