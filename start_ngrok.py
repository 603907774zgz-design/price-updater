#!/usr/bin/env python3
from pyngrok import ngrok
import time

try:
    tunnel = ngrok.connect(8000, 'http')
    public_url = tunnel.public_url
    
    print('='*70)
    print('🎉 ngrok公网隧道已启动！')
    print('='*70)
    print(f'公网URL: {public_url}')
    print(f'')
    print(f'📢 飞书Webhook配置地址：')
    print(f'{public_url}/feishu/webhook')
    print('='*70)
    print('')
    print('⚠️  请将此URL填入飞书后台「事件与回调」的「请求地址URL」')
    print('='*70)
    
    # 保持运行
    while True:
        time.sleep(1)
        
except KeyboardInterrupt:
    ngrok.kill()
    print('已停止')
