# ielts-buddy 每日日报：systemd 安装说明（需要 root）

## 安装
```bash
sudo cp /home/dsh/.dsh/bot/workspace/ielts-buddy/systemd/ielts-daily.service /etc/systemd/system/
sudo cp /home/dsh/.dsh/bot/workspace/ielts-buddy/systemd/ielts-daily.timer   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ielts-daily.timer
```

## 验证
```bash
systemctl list-timers ielts-daily.timer
systemctl start ielts-daily.service        # 手动跑一次
journalctl -u ielts-daily.service -n 50    # 或看 ~/.ielts-buddy/logs/systemd-daily.log
```

## 卸载
```bash
sudo systemctl disable --now ielts-daily.timer
sudo rm /etc/systemd/system/ielts-daily.{service,timer}
sudo systemctl daemon-reload
```

## 说明
- 定时：每天 09:00（Asia/Shanghai），错过会补跑（Persistent=true）。
- 流水线：生成当天日报 -> 推送 gh-pages（触发 Pages 部署）-> 发送邮件。
- 凭据：`~/.ielts-buddy/email.json`（600）、`~/.ielts-buddy/.gh-token`（600），不落仓库。
- 日志：`~/.ielts-buddy/logs/daily-YYYY-MM-DD.log`、`daemon.log`、`systemd-daily.log`。
- 临时兜底：systemd timer 未安装时，`~/.ielts-buddy/bin/ensure-ielts.sh` 会拉起常驻 daemon；
  Keeper 在每次 harness 重启检查时可调用它（幂等）。
