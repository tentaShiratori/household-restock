# 導入スキルのソース固定

| skill | 配置 | ソース | commit | ライセンス |
| --- | --- | --- | --- | --- |
| `i-have-adhd` | `.agents/skills/i-have-adhd/` | [ayghri/i-have-adhd](https://github.com/ayghri/i-have-adhd) | `1ecea1993b7fce257ffbd686c070948b5e07eda6` | MIT |
| `yomiyasu` | `.agents/skills/yomiyasu/` | [nanaism/yomiyasu](https://github.com/nanaism/yomiyasu) | `8394e099486aaa2e28cf89992e46f5ebe5ed839d` | MIT（metadata version 2.5.0） |

## ロックファイルの限界

`skills-lock.json` は `source` / `computedHash` / `installMode` を持つが、**Git ref（commit）は持たない**。  
そのため `skills experimental_install` だけでは、上表の commit からの復元を保証しない。commit 固定の再取得は:

```bash
mise exec -- skills add 'ayghri/i-have-adhd#1ecea1993b7fce257ffbd686c070948b5e07eda6' --skill i-have-adhd -a cursor -y --copy
mise exec -- skills add 'nanaism/yomiyasu#8394e099486aaa2e28cf89992e46f5ebe5ed839d' --skill yomiyasu -a cursor -y --copy
```

（skills 1.7.6 では `@` は skill 名、`#` が ref。詳細は [AGENTS.md](../AGENTS.md)）

同梱の `.agents/skills/` が作業用の正。上流ファイルは改造しない。
