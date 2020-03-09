#! /usr/bin/env python3

import argparse
import atexit
import os
import signal
import subprocess
import time
import unittest

from hwilib.cli import process_commands
from test_device import DeviceTestCase, start_bitcoind, TestDeviceConnect, TestDisplayAddress, TestGetKeypool, TestGetDescriptors, TestSignMessage, TestSignTx

def coldcard_test_suite(simulator, rpc, userpass, interface):
    # Start the Coldcard simulator
    coldcard_proc = subprocess.Popen(['python3', os.path.basename(simulator), '-m'], cwd=os.path.dirname(simulator), stdout=subprocess.DEVNULL, preexec_fn=os.setsid)
    # Wait for simulator to be up
    while True:
        try:
            enum_res = process_commands(['enumerate'])
            found = False
            for dev in enum_res:
                if dev['type'] == 'coldcard' and 'error' not in dev:
                    found = True
                    break
            if found:
                break
        except:
            pass
        time.sleep(0.5)
    # Cleanup

    def cleanup_simulator():
        os.killpg(os.getpgid(coldcard_proc.pid), signal.SIGTERM)
        os.waitpid(os.getpgid(coldcard_proc.pid), 0)
    atexit.register(cleanup_simulator)

    # Coldcard specific management command tests
    class TestColdcardManCommands(DeviceTestCase):
        def test_setup(self):
            result = self.do_command(self.dev_args + ['-i', 'setup'])
            self.assertIn('error', result)
            self.assertIn('code', result)
            self.assertEqual(result['error'], 'The Coldcard does not support software setup')
            self.assertEqual(result['code'], -9)

        def test_wipe(self):
            result = self.do_command(self.dev_args + ['wipe'])
            self.assertIn('error', result)
            self.assertIn('code', result)
            self.assertEqual(result['error'], 'The Coldcard does not support wiping via software')
            self.assertEqual(result['code'], -9)

        def test_restore(self):
            result = self.do_command(self.dev_args + ['-i', 'restore'])
            self.assertIn('error', result)
            self.assertIn('code', result)
            self.assertEqual(result['error'], 'The Coldcard does not support restoring via software')
            self.assertEqual(result['code'], -9)

        def test_backup(self):
            result = self.do_command(self.dev_args + ['backup'])
            self.assertTrue(result['success'])
            self.assertIn('The backup has been written to', result['message'])
            backup_filename = result['message'].split(' ')[-1]
            os.remove(backup_filename)

        def test_pin(self):
            result = self.do_command(self.dev_args + ['promptpin'])
            self.assertIn('error', result)
            self.assertIn('code', result)
            self.assertEqual(result['error'], 'The Coldcard does not need a PIN sent from the host')
            self.assertEqual(result['code'], -9)

            result = self.do_command(self.dev_args + ['sendpin', '1234'])
            self.assertIn('error', result)
            self.assertIn('code', result)
            self.assertEqual(result['error'], 'The Coldcard does not need a PIN sent from the host')
            self.assertEqual(result['code'], -9)

    class TestColdcardGetXpub(DeviceTestCase):
        def test_getxpub(self):
            result = self.do_command(self.dev_args + ['--expert', 'getxpub', 'm/44h/0h/0h/3'])
            self.assertEqual(result['xpub'], 'tpubDFHiBJDeNvqPWNJbzzxqDVXmJZoNn2GEtoVcFhMjXipQiorGUmps3e5ieDGbRrBPTFTh9TXEKJCwbAGW9uZnfrVPbMxxbFohuFzfT6VThty')
            self.assertTrue(result['testnet'])
            self.assertFalse(result['private'])
            self.assertEqual(result['depth'], 4)
            self.assertEqual(result['parent_fingerprint'], 'bc123c3e')
            self.assertEqual(result['child_num'], 3)
            self.assertEqual(result['chaincode'], '806b26507824f73bc331494afe122f428ef30dde80b2c1ce025d2d03aff411e7')
            self.assertEqual(result['pubkey'], '0368000bdff5e0b71421c37b8514de8acd4d98ba9908d183d9da56d02ca4fcfd08')
    
    class TestColdcardMultisigEnrollment(DeviceTestCase):
        def test_enroll_multisig(self):
            enrollment_file_contents = """
            Name: test
            Policy: 2 of 2
            Derivation: m/48'/1'/0'
            Format: P2WSH

            9d033c9d: tpubDC65zr1UjvBnuJERg1Fp4KdDwaLHEN4QViCm1F41A8ZoTachjgdKo38RCFbnWfiWRW8hg9DTbaGCkUSc5zXCNfW2KJ2KBJe94YFCGyshZ1J
            0f056943: tpubDDpWvmUrPZrhSPmUzCMBHffvC3HyMAPnWDSAQNBTnj1iZeJa7BZQEttFiP4DS4GCcXQHezdXhn86Hj6LHX5EDstXPWrMaSneRWM8yUf6NFd
            """
            result = self.do_command(self.dev_args + ['enrollmultisig', enrollment_file_contents])
            self.assertTrue(result['success'])

    # Generic device tests
    suite = unittest.TestSuite()
    suite.addTest(DeviceTestCase.parameterize(TestColdcardManCommands, rpc, userpass, 'coldcard', 'coldcard', '/tmp/ckcc-simulator.sock', '0f056943', '', interface=interface))
    suite.addTest(DeviceTestCase.parameterize(TestColdcardGetXpub, rpc, userpass, 'coldcard', 'coldcard', '/tmp/ckcc-simulator.sock', '0f056943', 'tpubDDpWvmUrPZrhSPmUzCMBHffvC3HyMAPnWDSAQNBTnj1iZeJa7BZQEttFiP4DS4GCcXQHezdXhn86Hj6LHX5EDstXPWrMaSneRWM8yUf6NFd', interface=interface))
    suite.addTest(DeviceTestCase.parameterize(TestColdcardMultisigEnrollment, rpc, userpass, 'coldcard', 'coldcard', '/tmp/ckcc-simulator.sock', '0f056943', 'tpubDDpWvmUrPZrhSPmUzCMBHffvC3HyMAPnWDSAQNBTnj1iZeJa7BZQEttFiP4DS4GCcXQHezdXhn86Hj6LHX5EDstXPWrMaSneRWM8yUf6NFd', interface=interface))
    suite.addTest(DeviceTestCase.parameterize(TestDeviceConnect, rpc, userpass, 'coldcard', 'coldcard', '/tmp/ckcc-simulator.sock', '0f056943', 'tpubDDpWvmUrPZrhSPmUzCMBHffvC3HyMAPnWDSAQNBTnj1iZeJa7BZQEttFiP4DS4GCcXQHezdXhn86Hj6LHX5EDstXPWrMaSneRWM8yUf6NFd', interface=interface))
    suite.addTest(DeviceTestCase.parameterize(TestDeviceConnect, rpc, userpass, 'coldcard_simulator', 'coldcard', '/tmp/ckcc-simulator.sock', '0f056943', 'tpubDDpWvmUrPZrhSPmUzCMBHffvC3HyMAPnWDSAQNBTnj1iZeJa7BZQEttFiP4DS4GCcXQHezdXhn86Hj6LHX5EDstXPWrMaSneRWM8yUf6NFd', interface=interface))
    suite.addTest(DeviceTestCase.parameterize(TestGetDescriptors, rpc, userpass, 'coldcard', 'coldcard', '/tmp/ckcc-simulator.sock', '0f056943', 'tpubDDpWvmUrPZrhSPmUzCMBHffvC3HyMAPnWDSAQNBTnj1iZeJa7BZQEttFiP4DS4GCcXQHezdXhn86Hj6LHX5EDstXPWrMaSneRWM8yUf6NFd', interface=interface))
    suite.addTest(DeviceTestCase.parameterize(TestGetKeypool, rpc, userpass, 'coldcard', 'coldcard', '/tmp/ckcc-simulator.sock', '0f056943', 'tpubDDpWvmUrPZrhSPmUzCMBHffvC3HyMAPnWDSAQNBTnj1iZeJa7BZQEttFiP4DS4GCcXQHezdXhn86Hj6LHX5EDstXPWrMaSneRWM8yUf6NFd', interface=interface))
    suite.addTest(DeviceTestCase.parameterize(TestDisplayAddress, rpc, userpass, 'coldcard', 'coldcard', '/tmp/ckcc-simulator.sock', '0f056943', 'tpubDDpWvmUrPZrhSPmUzCMBHffvC3HyMAPnWDSAQNBTnj1iZeJa7BZQEttFiP4DS4GCcXQHezdXhn86Hj6LHX5EDstXPWrMaSneRWM8yUf6NFd', interface=interface))
    suite.addTest(DeviceTestCase.parameterize(TestSignMessage, rpc, userpass, 'coldcard', 'coldcard', '/tmp/ckcc-simulator.sock', '0f056943', 'tpubDDpWvmUrPZrhSPmUzCMBHffvC3HyMAPnWDSAQNBTnj1iZeJa7BZQEttFiP4DS4GCcXQHezdXhn86Hj6LHX5EDstXPWrMaSneRWM8yUf6NFd', interface=interface))
    suite.addTest(DeviceTestCase.parameterize(TestSignTx, rpc, userpass, 'coldcard', 'coldcard', '/tmp/ckcc-simulator.sock', '0f056943', 'tpubDDpWvmUrPZrhSPmUzCMBHffvC3HyMAPnWDSAQNBTnj1iZeJa7BZQEttFiP4DS4GCcXQHezdXhn86Hj6LHX5EDstXPWrMaSneRWM8yUf6NFd', interface=interface))
    return suite

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test Coldcard implementation')
    parser.add_argument('simulator', help='Path to the Coldcard simulator')
    parser.add_argument('bitcoind', help='Path to bitcoind binary')
    parser.add_argument('--interface', help='Which interface to send commands over', choices=['library', 'cli', 'bindist'], default='library')
    args = parser.parse_args()

    # Start bitcoind
    rpc, userpass = start_bitcoind(args.bitcoind)

    suite = coldcard_test_suite(args.simulator, rpc, userpass, args.interface)
    unittest.TextTestRunner(verbosity=2).run(suite)
