from pathlib import Path
import duckdb

db_path = Path("data/quality.duckdb")
output_path = Path("data/exported_parquet")
def export_and_inspect_tables(db_path , output_dir):
    if not db_path.exists():
        raise FileNotFoundError(f"database not found: {db_path.resolve()}")
    output_dir.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        # get all table names
        tables = [row[0] for row in con.execute("SHOW TABLES").fetchall()]
        if not tables:
            print("no tables found in the database")
            return
        for table_name in tables:
            print(f"table: {table_name}")
            # safely quote the table name
            quoted_table = '"' + table_name.replace('"', '""') + '"'
            # display column names and data types
            schema = con.execute(f"DESCRIBE SELECT * FROM {quoted_table}").fetchall()
            print("\ncolumns and data types:")
            for column in schema:
                print(f"{column[0]}: {column[1]}")
            # count rows in the database table
            row_count = con.execute(f"SELECT COUNT(*) FROM {quoted_table}").fetchone()[0]
            print(f"\ntotal rows in DuckDB: {row_count}")
            # display the first five rows
            cursor = con.execute(f"SELECT * FROM {quoted_table} LIMIT 5")
            column_names = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            print("\nfirst five rows:")
            print(" | ".join(column_names))
            for row in rows:
                print(" | ".join(str(value) for value in row))
            # export the table to a Parquet file
            output_path = (output_dir / f"{table_name}.parquet").resolve()
            sql_path = str(output_path).replace("'", "''")
            con.execute(f"COPY (SELECT * FROM {quoted_table}) TO '{sql_path}' (FORMAT PARQUET)")
            print(f"\nexported to: {output_path}")
            # read the exported file and verify its row count
            parquet_count = con.execute("SELECT COUNT(*) FROM read_parquet(?)", [str(output_path)]).fetchone()[0]
            print(f"rows in Parquet: {parquet_count}")
            print(f"row counts match: {row_count == parquet_count}")
    finally:
        con.close()

def main() -> None:
    export_and_inspect_tables(db_path, output_path)

if __name__ == "__main__":
    main()