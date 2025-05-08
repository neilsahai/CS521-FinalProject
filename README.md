# CS521-FinalProject

Neil Sahai:
Worked on the Difficulty Adjustment script. Created a script that simulates timestamps, and based on the timestamps simulates the difficulty according to bitcoin design. 


Yuhang Li:
Worked on evaluating the multi-processing miner. Captured a real job from the mining pool and measured the speed of nonce guessing with different numbers of processes.


Mei Han:
Worked on using random nonces as an alternative to serial nonce incrementation in mining. Since this approach is already implemented as an existing solution, my contribution focused on reviewing and validating the execution of the code in [solo_miner.py](https://github.com/iceland2k14/solominer/blob/main/solo_miner.py)


Xing Gao:
Executed and analyzed the end-to-end mining workflow of [PythonBitcoinMiner](https://github.com/HugoXOX3/PythonBitcoinMiner.git). Ran the script against a live solo CKPool, logged the Stratum message sequence (subscribe → authorize → notify → submit), observed “Nonce found” and “Above target” responses, and validated that the miner correctly implements the Proof-of-Work loop and share‐submission logic.

