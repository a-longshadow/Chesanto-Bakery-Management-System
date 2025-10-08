"""
Excel Workbook Analyzer for Chesanto Bakery Management System
"""
import pandas as pd
import json
from pathlib import Path
import numpy as np
from datetime import datetime

class WorkbookAnalyzer:
    def __init__(self, excel_path):
        self.excel_path = Path(excel_path)
        self.output_dir = self.excel_path.parent / 'analysis_output'
        self.output_dir.mkdir(exist_ok=True)
        
    def analyze_workbook(self):
        """Main analysis function"""
        print(f"Analyzing {self.excel_path.name}...")
        
        # Read all sheets (with no data yet)
        excel = pd.ExcelFile(self.excel_path)
        sheet_names = excel.sheet_names
        
        workbook_analysis = {
            'filename': self.excel_path.name,
            'analysis_date': datetime.now().isoformat(),
            'total_sheets': len(sheet_names),
            'sheets': []
        }
        
        # Analyze each sheet
        for sheet_name in sheet_names:
            print(f"Analyzing sheet: {sheet_name}")
            sheet_analysis = self.analyze_sheet(excel, sheet_name)
            workbook_analysis['sheets'].append(sheet_analysis)
            
        # Save analysis results
        self.save_analysis(workbook_analysis)
        
    def analyze_sheet(self, excel, sheet_name):
        """Analyze a single worksheet"""
        # Read first few rows to analyze structure
        df = pd.read_excel(excel, sheet_name=sheet_name, nrows=100)
        
        sheet_analysis = {
            'name': sheet_name,
            'column_count': len(df.columns),
            'sample_row_count': len(df),
            'columns': self.analyze_columns(df),
            'potential_keys': self.identify_potential_keys(df),
            'has_formulas': self.check_for_formulas(df),
            'data_types': self.get_data_types(df)
        }
        
        return sheet_analysis
    
    def analyze_columns(self, df):
        """Analyze column properties"""
        columns = []
        for col in df.columns:
            col_info = {
                'name': str(col),
                'dtype': str(df[col].dtype),
                'null_count': df[col].isnull().sum(),
                'unique_values': df[col].nunique(),
                'sample_values': df[col].dropna().head(3).tolist()
            }
            columns.append(col_info)
        return columns
    
    def identify_potential_keys(self, df):
        """Identify columns that might be primary keys"""
        potential_keys = []
        for col in df.columns:
            if df[col].nunique() == len(df) and df[col].notna().all():
                potential_keys.append(str(col))
        return potential_keys
    
    def check_for_formulas(self, df):
        """Basic check for formula presence (this is limited without openpyxl)"""
        return any('=' in str(val) for val in df.values.flatten() if isinstance(val, str))
    
    def get_data_types(self, df):
        """Get unique data types in the sheet"""
        return list(set(df.dtypes.astype(str).tolist()))
    
    def save_analysis(self, analysis):
        """Save analysis results to JSON"""
        def convert_to_json_serializable(obj):
            if isinstance(obj, (np.int64, np.int32)):
                return int(obj)
            if isinstance(obj, (np.float64, np.float32)):
                return float(obj)
            if isinstance(obj, np.bool_):
                return bool(obj)
            if isinstance(obj, (datetime, pd.Timestamp)):
                return obj.isoformat()
            if isinstance(obj, (pd.Series, pd.DataFrame)):
                return obj.to_dict()
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj

        def convert_dict(d):
            if isinstance(d, dict):
                return {k: convert_dict(convert_to_json_serializable(v)) for k, v in d.items()}
            elif isinstance(d, list):
                return [convert_dict(convert_to_json_serializable(v)) for v in d]
            return convert_to_json_serializable(d)

        json_safe_analysis = convert_dict(analysis)
        
        output_file = self.output_dir / 'workbook_analysis.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(json_safe_analysis, f, indent=2)
        print(f"Analysis saved to {output_file}")
        
        # Generate markdown summary
        self.generate_markdown_summary(json_safe_analysis)
    
    def generate_markdown_summary(self, analysis):
        """Generate a markdown summary of the analysis"""
        md_path = self.output_dir / 'analysis_summary.md'
        
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# {analysis['filename']} Analysis Summary\n\n")
            f.write(f"Analysis Date: {analysis['analysis_date']}\n\n")
            f.write(f"Total Sheets: {analysis['total_sheets']}\n\n")
            
            f.write("## Sheet Overview\n\n")
            f.write("| Sheet Name | Columns | Sample Rows | Data Types | Potential Keys |\n")
            f.write("|------------|----------|-------------|-------------|----------------|\n")
            
            for sheet in analysis['sheets']:
                data_types = ', '.join(sheet['data_types'])
                keys = ', '.join(sheet['potential_keys']) if sheet['potential_keys'] else 'None'
                f.write(f"| {sheet['name']} | {sheet['column_count']} | {sheet['sample_row_count']} | {data_types} | {keys} |\n")
            
            f.write("\n## Detailed Analysis\n\n")
            for sheet in analysis['sheets']:
                f.write(f"\n### {sheet['name']}\n\n")
                f.write("#### Columns\n\n")
                f.write("| Column Name | Data Type | Null Count | Unique Values | Sample Values |\n")
                f.write("|-------------|-----------|------------|---------------|---------------|\n")
                
                for col in sheet['columns']:
                    samples = str(col['sample_values']).replace('|', ',')
                    f.write(f"| {col['name']} | {col['dtype']} | {col['null_count']} | {col['unique_values']} | {samples} |\n")
                
                f.write(f"\nHas Formulas: {sheet['has_formulas']}\n")

        print(f"Markdown summary saved to {md_path}")

if __name__ == "__main__":
    # Path to the Excel workbook (Windows compatible)
    WORKBOOK_PATH = Path(r"C:\Users\6lack_5wan\Documents\GITHUB-PROJECTS\Chesanto_App\Docs\Local_woking_docs\Chesantto Books_September 2025_.xlsx")
    
    try:
        analyzer = WorkbookAnalyzer(WORKBOOK_PATH)
        analyzer.analyze_workbook()
    except Exception as e:
        print(f"Error analyzing workbook: {e}")
        import traceback
        traceback.print_exc()