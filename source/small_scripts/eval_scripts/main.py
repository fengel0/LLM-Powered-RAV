from constants import DATASET_MAP, DATASETS, EVAL_CFGS, SYSTEM_CFGS, get_base_dataframe
from dataframe_handler import ratings_df
import pandas as pd
from filter import (
    build_all_agree,
    build_array,
    build_most_agree,
    filter_by_dataset,
    filter_by_eval_config,
    filter_by_system,
    load_eval_config,
    load_questions,
    load_ratings,
    prepare_summary,
)
from save_csv import export_metric_groups, save_figure
from plot import build_boxplot


folder_save = "./tmp"
base_path = "./evaluation_results"

prod_ratings = f"{base_path}/prod/rating_prod.csv"
prod_questions = f"{base_path}/prod/testsample.csv"
sys_configs = f"{base_path}/systemconfigs.csv"


def main():
    questions = load_questions(prod_questions)
    ratings = load_ratings(prod_ratings)

    for dataset in DATASETS:
        return_dataframe = get_base_dataframe()
        plot_dataframe_all_agree = get_base_dataframe()
        plot_dataframe_most_agree = get_base_dataframe()
        filtert_by_dataset = filter_by_dataset(
            eval=ratings,
            dataset_map=questions,
            dataset=dataset,
        )
        for sys_config_tuple in SYSTEM_CFGS:
            sys_config = sys_config_tuple[1]
            filtert_by_dataset_and_system = filter_by_system(
                eval=filtert_by_dataset,
                system_config_to_consider=sys_config,
            )
            ratings_array = build_array(filtert_by_dataset_and_system)

            most_agree_array = build_most_agree(
                ratings_array, system_config_id=sys_config
            )
            ratings_most_agree = ratings_df(
                ratings=most_agree_array,
                dataset=dataset,
                sys_config=sys_config,
            )

            all_agree_array = build_all_agree(ratings_array, system_config=sys_config)
            ratings_all_agree = ratings_df(
                ratings=all_agree_array,
                dataset=dataset,
                sys_config=sys_config,
            )

            return_dataframe = pd.concat(
                [
                    return_dataframe,
                    prepare_summary(ratings_all_agree),
                ],
                ignore_index=True,
            )
            plot_dataframe_all_agree = pd.concat(
                [
                    plot_dataframe_all_agree,
                    ratings_all_agree,
                ],
                ignore_index=True,
            )

            return_dataframe = pd.concat(
                [
                    return_dataframe,
                    prepare_summary(ratings_most_agree),
                ],
                ignore_index=True,
            )
            plot_dataframe_most_agree = pd.concat(
                [
                    plot_dataframe_most_agree,
                    ratings_most_agree,
                ],
                ignore_index=True,
            )

            for eval_system in EVAL_CFGS:
                eval_system_config_id = eval_system[1]
                tmp = filter_by_eval_config(
                    ratings=ratings_array, eval_config_id=eval_system_config_id
                )
                rating_results = ratings_df(
                    ratings=tmp, dataset=dataset, sys_config=sys_config
                )
                return_dataframe = pd.concat(
                    [return_dataframe, prepare_summary(rating_results)],
                    ignore_index=True,
                )

        eval_config_map = {e[1]: e[0] for e in EVAL_CFGS}
        sys_config_map = {e[1]: e[0] for e in SYSTEM_CFGS}
        eval_config_map["all-agree"] = "all-agree"
        eval_config_map["most-agree"] = "most-agree"
        return_dataframe.to_csv(f"./{folder_save}/{dataset}.csv")
        export_metric_groups(
            evaluation=return_dataframe,
            sys_config_map=sys_config_map,
            eval_config_map=eval_config_map,
            folder_to_store=folder_save,
            dataset_map=DATASET_MAP,
        )
        save_figure(
            build_boxplot(
                df=plot_dataframe_most_agree,
                eval_config_id="most-agree",
                system_config_id_map=sys_config_map,
                eval_config_id_map=eval_config_map,
                dataset=DATASET_MAP[dataset],
            ),
            DATASET_MAP[dataset],
            "most-agree",
            folder_save,
        )
        save_figure(
            build_boxplot(
                df=plot_dataframe_all_agree,
                eval_config_id="all-agree",
                system_config_id_map=sys_config_map,
                eval_config_id_map=eval_config_map,
                dataset=DATASET_MAP[dataset],
            ),
            DATASET_MAP[dataset],
            "all-agree",
            folder_save,
        )
        ratings_array = build_array(filtert_by_dataset)
        for eval_system in EVAL_CFGS:
            eval_system_config_id = eval_system[1]
            tmp = filter_by_eval_config(
                ratings=ratings_array, eval_config_id=eval_system_config_id
            )
            rating_results = ratings_df(ratings=tmp, dataset=dataset, sys_config="")
            save_figure(
                build_boxplot(
                    df=rating_results,
                    eval_config_id=eval_system_config_id,
                    system_config_id_map=sys_config_map,
                    eval_config_id_map=eval_config_map,
                    dataset=DATASET_MAP[dataset],
                ),
                DATASET_MAP[dataset],
                eval_config_map[eval_system_config_id],
                folder_save,
            )


main()
