import os
import sys
import pathlib
import argparse
import pandas as pd
import plotnine as gg
import matplotlib.pyplot as plt
import seaborn as sns

sys.path.append(os.path.join("..", "scripts"))
from config_utils import process_config_file
from cell_quality_utils import CellQuality

config_file = "site_processing_config_CP151A1.yaml"
force = True
config = process_config_file(config_file)

#Defines the sections of the config file
core_args = config["core"]
spot_args = config["process-spots"]
cell_args = config["process-cells"]
summ_cell_args = config["summarize-cells"]

#Defines the variables set in the config file
batch = core_args["batch"]
quality_func = core_args["categorize_cell_quality"]

barcode_cols = spot_args["barcode_cols"]
barcode_cols = ["Metadata_Foci_" + col for col in barcode_cols]
gene_cols = spot_args["gene_cols"]
gene_cols = ["Metadata_Foci_" + col for col in gene_cols]
spot_score_cols = spot_args["spot_score_cols"]
spot_score_count_cols = ["Metadata_Foci_" + col + "_count" for col in spot_score_cols]
spot_score_mean_cols = ["Metadata_Foci_" + col + "_mean" for col in spot_score_cols]

input_basedir = cell_args["output_basedir"]
metadata_foci_col = cell_args["metadata_merge_columns"]["cell_quality_col"]
cell_cols = cell_args["metadata_merge_columns"]["cell_cols"]
cell_quality_col = cell_args["metadata_merge_columns"]["cell_quality_col"]
foci_site_col = cell_args["foci_site_col"]

output_resultsdir = summ_cell_args["output_resultsdir"]
output_figuresdir = summ_cell_args["output_figuresdir"]
cell_category_order = summ_cell_args["cell_category_order"]
cell_category_colors = summ_cell_args["cell_category_colors"]

cell_quality = CellQuality(quality_func)
cell_category_dict = cell_quality.define_cell_quality()
empty_cell_category = len(cell_category_dict) + 1
cell_category_dict[empty_cell_category] = "Empty"
cell_category_df = pd.DataFrame(cell_category_dict, index=["Cell_Class"])
cell_category_list = list(cell_category_dict.values())

# Read and Merge Data
cell_quality_list = []
metadata_list = []
metadata_col_list = []
metadata_col_list.append("Cell_Class")
metadata_col_list.extend(cell_cols)
metadata_col_list.extend(barcode_cols)
metadata_col_list.extend(gene_cols)
metadata_col_list.extend(spot_score_count_cols)
metadata_col_list.extend(spot_score_mean_cols)
metadata_col_list.append(cell_quality_col)
metadata_col_list.append(foci_site_col)

input_dir = pathlib.Path(input_basedir, batch, "paint")
sites = os.listdir(input_dir)
print(f"There are {len(sites)} sites.")

for site in sites:

    cell_count_file = pathlib.Path(input_dir, site, f"cell_counts_{site}.tsv")
    metadata_file = pathlib.Path(input_dir, site, f"metadata_{site}.tsv.gz")

    # Aggregates cell quality by site into single list
    cell_quality_list.append(pd.read_csv(cell_count_file, sep='\t'))

    # Aggregates metadata by site into a single list
    metadata_df = (
        pd
        .read_csv(metadata_file, sep='\t')
        .loc[:,metadata_col_list]
        .reset_index(drop=True)
    )

    metadata_list.append(metadata_df)

# Creates dataframe from cell quality list
cell_count_df = pd.concat(cell_quality_list, axis="rows").reset_index(drop=True)

# Assigns the Cell_Quality column to the category datatype and sets categories
cell_count_df.loc[:, 'Cell_Quality'] = (
    pd.Categorical(
        cell_count_df.Cell_Quality,
        categories=cell_category_order
    )
)

# Assigns the Site column to the category datatype
cell_count_df.loc[:, "site"] = (
    pd.Categorical(
        cell_count_df.site,
        categories=(
            cell_count_df
            .groupby("site")
            ["cell_count"]
            .sum()
            .sort_values(ascending=False)
            .index
            .tolist()
        )
    )
)

cell_count_df = cell_count_df.assign(
    Plate=[x[0] for x in cell_count_df.site.str.split("-")],
    Well=[x[1] for x in cell_count_df.site.str.split("-")],
    Site=[x[2] for x in cell_count_df.site.str.split("-")]
)

output_file = pathlib.Path(output_resultsdir, "cells", "cell_count.tsv")
#cell_count_df.to_csv(output_file, sep='\t', index=False)

print(cell_count_df.shape)
cell_count_df.head(10)

# Graph: Cell count with all wells in same graph
cell_count_gg = (
    gg.ggplot(cell_count_df, gg.aes(x="Site", y="cell_count"))
    + gg.geom_bar(gg.aes(fill="Cell_Quality"), stat="identity")
    + gg.theme_bw()
    + gg.theme(axis_text_x = gg.element_text(rotation=90, size=5))
    + gg.xlab("Sites")
    + gg.ylab("Cell Count")
    + gg.scale_fill_manual(
        name="Cell Quality",
        labels = cell_category_list,
        values = cell_category_colors
    )
)

output_file = pathlib.Path(output_figuresdir, "all_cellpainting_cellquality_across_sites.png")
#cell_count_gg.save(output_file, dpi=300, width=10, height=7, verbose=False)

cell_count_gg

#Same graph as above, separated by Well.
well_order = cell_count_df['site'].unique()

cell_count_df.loc[:, 'Well'] = (
    pd.Categorical(
        cell_count_df.Well,
        categories=well_order
    )
)

cell_count_gg_parsed = (
    gg.ggplot(cell_count_df, gg.aes(x="Site", y="cell_count"))
    + gg.geom_bar(gg.aes(fill="Cell_Quality"), stat="identity")
    + gg.theme_bw()
    + gg.theme(axis_text_x = gg.element_text(rotation=90, size=5),
               strip_background = gg.element_rect(colour = "black", fill = "#fdfff4"))
    + gg.xlab("Sites")
    + gg.ylab("Cell Count")
    + gg.scale_fill_manual(
        name="Cell Quality",
        labels = cell_category_order,
        values = cell_category_colors
      )
    + gg.facet_wrap("~Well", nrow=2, ncol=2, drop=False, scales="free_x")
    )

output_file = pathlib.Path(output_figuresdir, "all_cellpainting_cellquality_across_sites_by_well.png")
#cell_count_gg_parsed.save(output_file, dpi=300, width=10, height=7, verbose=False)

cell_count_gg_parsed

#  Total cells in each quality category
all_count_df = pd.DataFrame(cell_count_df.groupby("Cell_Quality")["cell_count"].sum()).reset_index()
all_count_df

# Graph: Total cells in each quality category
all_cells = all_count_df.cell_count.sum()

total_cell_count_gg = (
    gg.ggplot(all_count_df, gg.aes(x="Cell_Quality", y="cell_count"))
    + gg.geom_bar(gg.aes(fill="Cell_Quality"), stat="identity")
    + gg.theme_bw()
    + gg.theme(axis_text_x = gg.element_text(rotation=90, size=9))
    + gg.xlab("")
    + gg.ylab("Cell Count")
    + gg.ggtitle(f"{all_cells} Total Cells")
    + gg.scale_fill_manual(
        name="Cell Quality",
        labels = cell_category_order,
        values = cell_category_colors,
    )
)

output_file = pathlib.Path(output_figuresdir, "total_cell_count.png")
#total_cell_count_gg.save(output_file, dpi=300, width=5, height=6, verbose=False)

total_cell_count_gg

print(f"There are a total of {all_cells} cells in {batch}")

# Total cell number by well
all_well_count_df = (
    pd.DataFrame(
        cell_count_df
        .groupby(
            [
                "Cell_Quality",
                "Well"
            ]
        )
        ["cell_count"]
        .sum()
    )
    .reset_index()
)

all_well_count_df

a1_sum = all_well_count_df.groupby("Well")["cell_count"].sum()["A1"]
a2_sum = all_well_count_df.groupby("Well")["cell_count"].sum()["A2"]

total_cell_well_count_gg = (
    gg.ggplot(all_well_count_df, gg.aes(x="Well", y="cell_count"))
    + gg.geom_bar(gg.aes(fill="Cell_Quality"), stat="identity")
    + gg.theme_bw()
    + gg.theme(axis_text_x = gg.element_text(rotation=90, size=9))
    + gg.xlab("")
    + gg.ylab("Cell Count")
    + gg.ggtitle(f"{a1_sum} A1 Total Cells\n{a2_sum} B2 Total Cells")
    + gg.facet_wrap("~Cell_Quality")
    + gg.scale_fill_manual(
        name="Cell Quality",
        labels = cell_category_order,
        values = cell_category_colors,
    )
    + gg.theme(strip_background = gg.element_rect(colour = "black", fill = "#fdfff4"))
)

output_file = pathlib.Path(output_figuresdir, "total_cell_count_by_well.png")
#total_cell_well_count_gg.save(output_file, dpi=400, width=6, height=5, verbose=False)

total_cell_well_count_gg
