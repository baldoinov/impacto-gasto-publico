import os
import pandas as pd
import basedosdados as bd

from dotenv import load_dotenv

load_dotenv()

BILLING_PROJECT_ID = os.getenv("BILLING_PROJECT_ID")


def main(path: str) -> pd.DataFrame:
    "Build and save the dataset used for regression analysis."

    spending = get_spending_data()
    oportunities = get_project_opportunities_access_data()
    population = get_populational_data()
    education = get_education_data()
    
    
    df = pd.merge(population, spending, how="left", on=["id_municipio", "sigla_uf"])
    df = pd.merge(df, oportunities, how="left", on=["id_municipio"])
    df = pd.merge(df, education, how="left", on=["id_municipio"])

    
    df.to_csv(path)

    return df


def get_project_opportunities_access_data() -> pd.DataFrame:
    """
    Fetch the data from "Projeto Acesso a Oportunidades". This project provides
    estimates of access to jobs, health, and education by mode of transport for
    the largest cities in Brazil. The research uses different indicators to
    estimate urban accessibility conditions disaggregated by socioeconomic
    groups and in high spatial resolution.
    """

    query = """
        SELECT
            id_municipio,
            SUM(quantidade_pessoas) AS quantidade_pessoas,
            SUM(quantidade_pessoas_brancas) AS quantidade_pessoas_brancas, 
            SUM(quantidade_pessoas_negras) AS quantidade_pessoas_negras,
            SUM(quantidade_pessoas_indigenas) AS quantidade_pessoas_indigenas,
            SUM(quantidade_pessoas_amarelas) AS quantidade_pessoas_amarelas,
            SUM(quantidade_estabelecimentos_ensino_infantil) AS quantidade_estabelecimentos_ensino_infantil,
            SUM(quantidade_estabelecimentos_ensino_fundamental) AS quantidade_estabelecimentos_ensino_fundamental,
            SUM(quantidade_estabelecimentos_ensino_medio) AS quantidade_estabelecimentos_ensino_medio
        FROM basedosdados.br_ipea_acesso_oportunidades.estatisticas_2019
        GROUP BY id_municipio
    """

    df = bd.read_sql(query, BILLING_PROJECT_ID)

    return df


def get_spending_data() -> pd.DataFrame:
    """
    Retrieves spending data for municipalities related to different
    categories of government spending.
    """
    query_total_spending = """
        SELECT id_municipio,
            sigla_uf,
            SUM(valor) AS total
            FROM basedosdados.br_me_siconfi.municipio_despesas_funcao
        WHERE ano = 2019
        GROUP BY id_municipio,
            sigla_uf
        ORDER BY id_municipio
    """
    df_total_spending = bd.read_sql(query_total_spending, BILLING_PROJECT_ID)

    query_spending_by_city = """
        SELECT id_municipio,
            sigla_uf,
            conta_bd,
            SUM(valor) AS valor
            FROM basedosdados.br_me_siconfi.municipio_despesas_funcao
        WHERE ano = 2019
            AND conta_bd IN (
                'Segurança Pública',
                'Policiamento',
                'Defesa Civil',
                'Demais Subfunções Segurança Pública',
                'Defesa Nacional',
                'Demais Subfunções Defesa Nacional',
                'Assistência Social',
                'Assistência à Criança e ao Adolescente',
                'Assistência Comunitária',
                'Previdência Social',
                'Previdência do Regime Estatutário',
                'Previdência Básica',
                'Demais Subfunções Previdência Social',
                'Previdência Especial',
                'Previdência Complementar'
            )
        GROUP BY id_municipio,
            sigla_uf,
            conta_bd
    """

    # Spendig in some categories
    public_security = [
        "Segurança Pública",
        "Policiamento",
        "Defesa Civil",
        "Demais Subfunções Segurança Pública",
        "Defesa Nacional",
        "Demais Subfunções Defesa Nacional",
    ]

    social_aid = [
        "Assistência Social",
        "Assistência à Criança e ao Adolescente",
        "Assistência Comunitária",
    ]

    pensions = [
        "Previdência Social",
        "Previdência do Regime Estatutário",
        "Previdência Básica",
        "Demais Subfunções Previdência Social",
        "Previdência Especial",
        "Previdência Complementar",
    ]
    df_spending_by_city = bd.read_sql(query_spending_by_city, BILLING_PROJECT_ID)
    df_spending_by_city = df_spending_by_city.pivot_table(
        index=["id_municipio", "sigla_uf"],
        columns="conta_bd",
        values="valor",
        aggfunc="sum",
    ).reset_index()

    df_spending_by_city = df_spending_by_city.assign(
        seguranca=df_spending_by_city[public_security].sum(axis=1),
        assistencia=df_spending_by_city[social_aid].sum(axis=1),
        previdencia=df_spending_by_city[pensions].sum(axis=1),
    )

    df = pd.merge(
        df_total_spending, df_spending_by_city, how="left", on=["id_municipio", "sigla_uf"]
    ).drop(columns=public_security + social_aid + pensions)

    return df


def get_education_data() -> pd.DataFrame:

    query = """
        SELECT id_municipio,
            AVG(taxa_abandono_ef) AS taxa_abandono_ef,
            AVG(taxa_reprovacao_ef) AS taxa_reprovacao_ef,
            AVG(taxa_aprovacao_ef) AS taxa_aprovacao_ef,
            AVG(taxa_abandono_em) AS taxa_abandono_em,
            AVG(taxa_reprovacao_em) AS taxa_reprovacao_em,
            AVG(taxa_aprovacao_em) AS taxa_aprovacao_em,
            AVG(atu_ei) AS atu_ei,
            AVG(atu_ef) AS atu_ef,
            AVG(atu_em) AS atu_em
        FROM basedosdados.br_inep_indicadores_educacionais.municipio
        WHERE ano = 2019
        GROUP BY id_municipio
    """
    df = bd.read_sql(query, BILLING_PROJECT_ID)

    return df


def get_populational_data() -> pd.DataFrame:

    query = """
        SELECT ano,
            sigla_uf,
            id_municipio,
            populacao
        FROM basedosdados.br_ibge_populacao.municipio
        WHERE ano = 2019
    """
    df = bd.read_sql(query, BILLING_PROJECT_ID)
    return df


if __name__ == "__main__":
    main("../data/processed/dataset-public-spending.csv")
