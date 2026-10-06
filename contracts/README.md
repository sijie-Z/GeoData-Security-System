# AnchorRegistry — EVM 第二锚定（Sepolia 测试网）

`AnchorRegistry.sol` 是最小时间戳注册合约：把证据批次的 merkle root（`bytes32`）
首次写入链上，记录当时 `block.timestamp`。**诚实定位**：Sepolia 测试网 demo，
只能证明"该 root 在某时刻之前已存在"（存在性下界），不做真实性背书；验证 UI 属后续波次。

全 Python 链路（py-solc-x 编译 + web3.py 部署/调用），不依赖 Hardhat/Node。
应用侧集成见 `testrealend/evidence/anchor.py` 的 `EVMAnchorProvider`
（未配置时 PENDING，绝不阻塞业务）。

## 文件

| 文件 | 用途 |
| --- | --- |
| `AnchorRegistry.sol` | 合约源码（Solidity ^0.8.20，用 solc 0.8.24 编译） |
| `deploy_evm_anchor.py` | 编译 + 部署脚本（`--network sepolia` 默认 / `--network tester` 内存链自测） |

## 前置

```bash
pip install "web3>=7" "py-solc-x>=2" "eth-tester[py-evm]>=0.11"
```

首次编译会经 py-solc-x 下载 solc 0.8.24（缓存在 `~/.solcx`，只需一次）。

## 部署步骤（Sepolia）

1. **生成钱包**（只打印地址，私钥写入 git 忽略的 `testrealend/instance/keys/evm_sepolia.key`）：

   ```bash
   cd testrealend
   python -m evidence.evm --new-key
   ```

2. **领测试币**（faucet 需人工/验证码，无法脚本化）：

   - https://cloud.google.com/application/web3/faucet/ethereum/sepolia
   - https://sepolia-faucet.pk910.de （浏览器 PoW 挖水）
   - https://www.alchemy.com/faucets/ethereum-sepolia
   - https://faucet.quicknode.com/ethereum/sepolia

3. **部署**（默认 RPC `https://ethereum-sepolia-rpc.publicnode.com`，可用 `EVM_RPC_URL` 覆盖）：

   ```bash
   python contracts/deploy_evm_anchor.py
   ```

   脚本只打印地址（部署者地址、合约地址、`EVM_CONTRACT_ADDRESS=...` 提示），**绝不打印私钥**。

4. **配置应用**：把脚本输出的合约地址写入运行环境：

   ```bash
   EVM_CONTRACT_ADDRESS=0x...   # 空则 EVMAnchorProvider 保持 PENDING，不影响现有业务
   ```

5. **本地自测**（内存链，无网络、无私钥）：

   ```bash
   python contracts/deploy_evm_anchor.py --network tester
   ```

## Etherscan 验证（verify）

1. 打开 `https://sepolia.etherscan.io/address/<合约地址>#code`
2. Verify and Publish → 选择 **Solidity (Single file)**
3. Compiler: `v0.8.24+commit.e11b9ed9`，License: `MIT`，Optimization: `No`
4. 粘贴 `AnchorRegistry.sol` 源码全文，提交验证

## 地址登记处

| 网络 | 部署者地址（只记地址） | 合约地址 | 部署 tx | 日期 |
| --- | --- | --- | --- | --- |
| Sepolia (11155111) | `0x17b43B48a0889b6B9eC58443CF67521fA418Fff3` | （部署后登记） | （部署后登记） | - |

合约地址部署后由部署者手工登记到本表（脚本会打印 `EVM_CONTRACT_ADDRESS=`行，直接复制）。

## 安全纪律

- 私钥只存在于 `testrealend/instance/keys/evm_sepolia.key`（`instance/` 已 gitignore），
  绝不入库/入 git/入日志/入 API 响应；本 README 只登记**地址**。
- 该钱包仅用于 Sepolia 测试网演示，不入金、不复用。
- 仓库从 `python -m evidence.evm --new-key` 生成的密钥如泄露，直接 `--force` 重生成并重新领水。
- 合约刻意最小（无 owner、无升级、无资金），避免引入多余攻击面。
