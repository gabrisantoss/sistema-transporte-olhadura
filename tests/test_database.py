from __future__ import annotations

import shutil
import unittest
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

from database import DB, DatabaseCorruptionError, backup_sqlite_file, restore_sqlite_backup


class DatabaseTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_root = Path(__file__).resolve().parent / ".tmp"
        self.temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = self.temp_root / f"case_{uuid4().hex}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.temp_dir / "teste.db"
        self.db = DB(path=self.db_path, seed_from_excel=False)

    def tearDown(self):
        if getattr(self, "db", None) is not None:
            self.db.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_salva_nota_e_contadores(self):
        self.db.adicionar_motorista(101, "Joao")
        self.db.adicionar_fazenda("100-001", "Fazenda Aurora")
        self.db.adicionar_variedade("RB001")

        motorista = self.db.resolver_referencia("motoristas", "101 - Joao")
        fazenda = self.db.resolver_referencia("fazendas", "Fazenda Aurora")
        variedade = self.db.resolver_referencia("variedades", "RB001", col_id="id")

        self.assertIsNotNone(motorista)
        self.assertIsNotNone(fazenda)
        self.assertIsNotNone(variedade)

        self.db.inserir_nota(
            {
                "numero": 1,
                "motorista_cod": motorista["codigo"],
                "motorista_nome": motorista["nome"],
                "caminhao": "ABC-1234",
                "operador_cod": None,
                "operador_nome": None,
                "colhedora": "12",
                "faz_muda_cod": fazenda["codigo"],
                "faz_muda_nome": fazenda["nome"],
                "talhao": "T1",
                "faz_plantio_cod": fazenda["codigo"],
                "faz_plantio_nome": fazenda["nome"],
                "variedade_id": variedade["id"],
                "variedade_nome": variedade["nome"],
                "data_colheita": "2026-03-27",
                "data_plantio": "2026-03-20",
            }
        )

        nota = self.db.buscar_nota(1)
        self.assertEqual("Joao", nota["motorista_nome"])
        self.assertEqual(1, self.db.contar_notas_total())
        self.assertEqual(1, self.db.contar_notas_data("2026-03-27"))

    def test_force_update_de_nota_existente(self):
        self.db.inserir_nota(
            {
                "numero": 2,
                "motorista_cod": 1,
                "motorista_nome": "Motorista A",
                "caminhao": "AAA-0001",
                "operador_cod": None,
                "operador_nome": None,
                "colhedora": "1",
                "faz_muda_cod": "100-001",
                "faz_muda_nome": "Origem",
                "talhao": "X1",
                "faz_plantio_cod": "100-002",
                "faz_plantio_nome": "Destino",
                "variedade_id": 1,
                "variedade_nome": "VAR-A",
                "data_colheita": "2026-03-27",
                "data_plantio": "2026-03-21",
            }
        )

        self.db.inserir_nota(
            {
                "numero": 2,
                "motorista_cod": 2,
                "motorista_nome": "Motorista B",
                "caminhao": "BBB-0002",
                "operador_cod": None,
                "operador_nome": None,
                "colhedora": "2",
                "faz_muda_cod": "100-010",
                "faz_muda_nome": "Nova Origem",
                "talhao": "Y1",
                "faz_plantio_cod": "100-020",
                "faz_plantio_nome": "Novo Destino",
                "variedade_id": 2,
                "variedade_nome": "VAR-B",
                "data_colheita": "2026-03-28",
                "data_plantio": "2026-03-22",
            },
            force=True,
        )

        nota = self.db.buscar_nota(2)
        self.assertEqual("Motorista B", nota["motorista_nome"])
        self.assertEqual("BBB-0002", nota["caminhao"])
        self.assertEqual("2026-03-28", nota["data_colheita"])

    def test_inserir_nota_rejeita_data_colheita_futura(self):
        data_futura = (date.today() + timedelta(days=1)).isoformat()

        with self.assertRaisesRegex(ValueError, "data atual do sistema"):
            self.db.inserir_nota(
                {
                    "numero": 20,
                    "motorista_cod": 1,
                    "motorista_nome": "Motorista Futuro",
                    "caminhao": "AAA-2020",
                    "operador_cod": None,
                    "operador_nome": None,
                    "colhedora": "20",
                    "faz_muda_cod": "100-001",
                    "faz_muda_nome": "Origem",
                    "talhao": "F1",
                    "faz_plantio_cod": "100-002",
                    "faz_plantio_nome": "Destino",
                    "variedade_id": 1,
                    "variedade_nome": "VAR-20",
                    "data_colheita": data_futura,
                    "data_plantio": date.today().isoformat(),
                }
            )

        self.assertIsNone(self.db.buscar_nota(20))

    def test_inserir_nota_rejeita_data_plantio_futura(self):
        data_futura = (date.today() + timedelta(days=1)).isoformat()

        with self.assertRaisesRegex(ValueError, "data atual do sistema"):
            self.db.inserir_nota(
                {
                    "numero": 21,
                    "motorista_cod": 1,
                    "motorista_nome": "Plantio Futuro",
                    "caminhao": "BBB-2021",
                    "operador_cod": None,
                    "operador_nome": None,
                    "colhedora": "21",
                    "faz_muda_cod": "100-001",
                    "faz_muda_nome": "Origem",
                    "talhao": "F2",
                    "faz_plantio_cod": "100-002",
                    "faz_plantio_nome": "Destino",
                    "variedade_id": 1,
                    "variedade_nome": "VAR-21",
                    "data_colheita": date.today().isoformat(),
                    "data_plantio": data_futura,
                }
            )

        self.assertIsNone(self.db.buscar_nota(21))

    def test_backup_e_restore(self):
        self.db.inserir_nota(
            {
                "numero": 3,
                "motorista_cod": 1,
                "motorista_nome": "Original",
                "caminhao": "CAM-001",
                "operador_cod": None,
                "operador_nome": None,
                "colhedora": "1",
                "faz_muda_cod": "100-001",
                "faz_muda_nome": "Origem",
                "talhao": "A1",
                "faz_plantio_cod": "100-002",
                "faz_plantio_nome": "Destino",
                "variedade_id": 1,
                "variedade_nome": "VAR-1",
                "data_colheita": "2026-03-27",
                "data_plantio": "2026-03-20",
            }
        )

        backup_path = self.temp_dir / "backup.db"
        self.db.create_backup(backup_path)

        self.db.inserir_nota(
            {
                "numero": 3,
                "motorista_cod": 2,
                "motorista_nome": "Alterado",
                "caminhao": "CAM-999",
                "operador_cod": None,
                "operador_nome": None,
                "colhedora": "9",
                "faz_muda_cod": "100-010",
                "faz_muda_nome": "Outra Origem",
                "talhao": "Z9",
                "faz_plantio_cod": "100-020",
                "faz_plantio_nome": "Outro Destino",
                "variedade_id": 9,
                "variedade_nome": "VAR-9",
                "data_colheita": "2026-03-29",
                "data_plantio": "2026-03-25",
            },
            force=True,
        )

        self.db.restore_from_backup(backup_path)
        nota = self.db.buscar_nota(3)
        self.assertEqual("Original", nota["motorista_nome"])
        self.assertEqual("CAM-001", nota["caminhao"])

    def test_backup_sqlite_file_copia_banco(self):
        self.db.inserir_nota(
            {
                "numero": 4,
                "motorista_cod": 1,
                "motorista_nome": "Teste",
                "caminhao": "XYZ-0001",
                "operador_cod": None,
                "operador_nome": None,
                "colhedora": "3",
                "faz_muda_cod": "100-001",
                "faz_muda_nome": "Origem",
                "talhao": "B2",
                "faz_plantio_cod": "100-002",
                "faz_plantio_nome": "Destino",
                "variedade_id": 1,
                "variedade_nome": "VAR-2",
                "data_colheita": "2026-03-27",
                "data_plantio": "2026-03-18",
            }
        )

        copia = self.temp_dir / "externo.db"
        backup_sqlite_file(self.db_path, copia)

        db_copia = DB(path=copia, seed_from_excel=False)
        try:
            nota = db_copia.buscar_nota(4)
            self.assertIsNotNone(nota)
            self.assertEqual("Teste", nota["motorista_nome"])
        finally:
            db_copia.close()

    def test_abertura_falha_quando_arquivo_esta_corrompido(self):
        corrompido = self.temp_dir / "corrompido.db"
        corrompido.write_bytes(b"isso nao eh um sqlite valido")

        with self.assertRaises(DatabaseCorruptionError):
            DB(path=corrompido, seed_from_excel=False)

    def test_restore_sqlite_backup_substitui_arquivo_corrompido(self):
        self.db.inserir_nota(
            {
                "numero": 5,
                "motorista_cod": 1,
                "motorista_nome": "Backup Integro",
                "caminhao": "RST-5000",
                "operador_cod": None,
                "operador_nome": None,
                "colhedora": "5",
                "faz_muda_cod": "100-001",
                "faz_muda_nome": "Origem",
                "talhao": "C3",
                "faz_plantio_cod": "100-002",
                "faz_plantio_nome": "Destino",
                "variedade_id": 1,
                "variedade_nome": "VAR-5",
                "data_colheita": "2026-03-27",
                "data_plantio": "2026-03-17",
            }
        )

        backup_path = self.temp_dir / "backup_integro.db"
        self.db.create_backup(backup_path)

        destino = self.temp_dir / "destino_corrompido.db"
        destino.write_bytes(b"conteudo quebrado")

        restaurado, quarantined = restore_sqlite_backup(destino, backup_path)
        self.assertEqual(destino, restaurado)
        self.assertIsNotNone(quarantined)
        self.assertTrue(quarantined.exists())

        db_restaurado = DB(path=destino, seed_from_excel=False)
        try:
            nota = db_restaurado.buscar_nota(5)
            self.assertIsNotNone(nota)
            self.assertEqual("Backup Integro", nota["motorista_nome"])
        finally:
            db_restaurado.close()


if __name__ == "__main__":
    unittest.main()
