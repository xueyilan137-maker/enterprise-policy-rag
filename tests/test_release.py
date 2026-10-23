import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from tools.prepare_release import build
from tools.verify_release import unpack


class ReleaseTests(unittest.TestCase):
    def test_private_files_excluded_and_approval_not_exported(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name, text in {'.local/password.json':'private', 'src/main.py':'pass',
                'data/eval/reserve-v1/human-reviews.json':'{"reviews":[{"evidence_file":"private"}]}',
                'random-dump.json':'unselected', '.git/config':'private'}.items():
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
            target=root/'result.zip';build(root,target)
            with zipfile.ZipFile(target) as archive:
                self.assertEqual(set(archive.namelist()), {'src/main.py','data/eval/reserve-v1/human-reviews.json','DELIVERY-MANIFEST.json'})
                self.assertEqual(json.loads(archive.read('data/eval/reserve-v1/human-reviews.json'))['reviews'], [])
            self.assertIn('private', (root/'data/eval/reserve-v1/human-reviews.json').read_text())
            with self.assertRaises(FileExistsError):build(root,target)

    def test_known_secret_blocks_release_without_echoing_value(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'.local').mkdir();(root/'src').mkdir()
            secret='fixture-private-value-123456789'
            (root/'.local/dataset-api.json').write_text(json.dumps({'DIFY_DATASET_API_KEY':secret}))
            (root/'src/leak.py').write_text('credential='+secret)
            with self.assertRaises(ValueError) as raised:build(root,root/'out.zip')
            self.assertNotIn(secret,str(raised.exception))
            self.assertFalse((root/'out.zip').exists())

    def test_bound_dataset_is_rejected_without_local_credentials(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'dify').mkdir()
            flow={'workflow':{'graph':{'nodes':[{'data':{'dataset_ids':['actual-dataset']}}]}}}
            (root/'dify/flow.template.yml').write_text(json.dumps(flow))
            with self.assertRaises(ValueError):build(root,root/'out.zip')

    def test_embedded_header_is_rejected_without_known_secret(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'dify').mkdir()
            flow={'workflow':{'graph':{'nodes':[{'data':{'type':'http-request',
                'url':'{{#env.API_URL#}}','headers':'Authorization: Bearer fixture-header-value'}}]}}}
            (root/'dify/flow.template.yml').write_text(json.dumps(flow))
            with self.assertRaises(ValueError):build(root,root/'out.zip')

    def test_tampered_archive_rejected_before_unpack(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);target=root/'unpacked';archive=root/'bad.zip'
            with zipfile.ZipFile(archive,'w') as out:
                out.writestr('src/main.py','changed')
                out.writestr('DELIVERY-MANIFEST.json',json.dumps({'files':{'src/main.py':'incorrect-hash'}}))
            with self.assertRaises(ValueError):unpack(archive,target)
            self.assertFalse(target.exists())

    def test_escaping_archive_path_rejected_before_unpack(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);archive=root/'bad.zip';target=root/'unpacked'
            with zipfile.ZipFile(archive,'w') as out:
                out.writestr('../outside.txt','data')
                out.writestr('DELIVERY-MANIFEST.json',json.dumps({'files':{'../outside.txt':'ignored'}}))
            with self.assertRaises(ValueError):unpack(archive,target)
            self.assertFalse(target.exists())


if __name__=='__main__':unittest.main()
