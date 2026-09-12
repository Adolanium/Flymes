import asyncio
import hashlib
import tempfile
import unittest
from pathlib import Path

from flymes.boundary import BoundaryError, WorkspaceBoundary, validate_demo_code
from flymes.hermes_adapter import HermesAdapter

BUG = 'def visible_items(items, query):\n    return [item for item in items if query in item]\n'
FIX = 'def visible_items(items, query):\n    return [item for item in items if query.casefold() in item.casefold()]\n'


class BoundaryTests(unittest.TestCase):
    def test_pure_filter_and_escape_rejection(self):
        validate_demo_code(BUG)
        validate_demo_code(FIX)
        attacks = ["import os\n" + FIX, FIX + '\nopen("outside", "w")',
                   FIX.replace('query.casefold()', 'eval(query)'),
                   FIX.replace('item.casefold()', 'item.__class__'),
                   FIX.replace('items, query', 'items, query=open("x")'),
                   '@print\n' + FIX, FIX.replace('return [', 'while True: pass\n    return [')]
        for code in attacks:
            with self.subTest(code=code), self.assertRaises(BoundaryError):
                validate_demo_code(code)

    def test_paths_and_compare_before_write(self):
        with tempfile.TemporaryDirectory(prefix='Flymes café space ') as tmp:
            root = Path(tmp)
            (root/'app.py').write_text(BUG)
            b = WorkspaceBoundary(root)
            for p in ['../app.py', 'C:/Windows/notepad.exe', 'app.py:secret', '..\\app.py']:
                with self.subTest(path=p), self.assertRaises((BoundaryError, FileNotFoundError)):
                    b.read(p)
            with self.assertRaises(BoundaryError):
                b.replace('app.py', FIX, 'bad hash')
            b.replace('app.py', FIX, hashlib.sha256(BUG.encode()).hexdigest())
            self.assertEqual(b.read('app.py'), FIX)
            self.assertIn('casefold', b.diff())


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='Flymes café space ')
        self.root = Path(self.tmp.name)
        (self.root/'app.py').write_text(BUG)

    async def asyncTearDown(self):
        self.tmp.cleanup()

    async def test_readonly_rejects_edit_and_shell(self):
        async def forbidden(**kwargs):
            return {'parsed': {'operation': 'replace', 'path': 'app.py', 'content': FIX}}
        a = HermesAdapter(self.root, llm=forbidden)
        r = await a.execute('INSPECT', 'task', 'r', 1)
        self.assertEqual(r['status'], 'error')
        self.assertEqual((self.root/'app.py').read_text(), BUG)

    async def test_duplicate_and_session_isolation(self):
        count = 0
        async def llm(**kwargs):
            nonlocal count
            count += 1
            return {'parsed': {'operation': 'done'}}
        a = HermesAdapter(self.root, llm=llm)
        x = await a.execute('SEARCH', 'task', 'r', 1)
        self.assertEqual(x, await a.execute('SEARCH', 'task', 'r', 1))
        self.assertEqual(count, 1)
        with self.assertRaises(BoundaryError):
            await a.execute('TEST', 'task', 'r', 1)
        with self.assertRaises(BoundaryError):
            await a.execute('SEARCH', 'task', 'other', 1)

    async def test_edit_and_independent_finish(self):
        async def llm(**kwargs):
            return {'parsed': {'operation': 'replace', 'path': 'app.py', 'content': FIX,
                               'expected_sha256': hashlib.sha256(BUG.encode()).hexdigest()}}
        a = HermesAdapter(self.root, llm=llm, verifier=lambda p: {'verified': False, 'failed': 1})
        r = await a.execute('IMPLEMENT', 'task', 'r', 1)
        self.assertEqual(r['status'], 'ok')
        self.assertEqual(r['model_calls'], 1)
        self.assertFalse((await a.execute('FINISH', 'task', 'r', 2))['verified'])

    async def test_cancel_discards_late_response(self):
        gate = asyncio.Event()
        async def llm(**kwargs):
            await gate.wait()
            return {'parsed': {'operation': 'replace', 'path': 'app.py', 'content': FIX,
                               'expected_sha256': hashlib.sha256(BUG.encode()).hexdigest()}}
        a = HermesAdapter(self.root, llm=llm)
        work = asyncio.create_task(a.execute('IMPLEMENT', 'task', 'r', 1))
        await asyncio.sleep(0)
        with self.assertRaises(BoundaryError):
            await a.execute('SEARCH', 'task', 'r', 2)
        a.cancel()
        gate.set()
        self.assertEqual((await work)['status'], 'cancelled')
        self.assertEqual((self.root/'app.py').read_text(), BUG)

    async def test_timeout(self):
        async def llm(**kwargs):
            await asyncio.sleep(1)
        a = HermesAdapter(self.root, llm=llm, timeout=0.01)
        self.assertEqual((await a.execute('SEARCH', 'task', 'r', 1))['status'], 'timeout')


if __name__ == '__main__':
    unittest.main()
