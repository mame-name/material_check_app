import pandas as pd

def process_requirements(df):
    """所要量一覧表の加工"""
    return df.fillna("")

def process_inventory(df):
    """在庫一覧表の加工"""
    return df.fillna(0)

def process_receipts(df):
    """受入表の加工"""
    return df.fillna("")
