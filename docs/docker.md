# Linux Docker 部署

Docker 部署面向单用户、单实例使用。容器内服务监听 `0.0.0.0:8765`，Compose 默认只把它发布到宿主机的 `127.0.0.1:8765`，避免没有身份认证的 EasyRead 被直接暴露到局域网或公网。

## 快速启动

使用 Docker Hub 上的最新镜像：

```bash
docker compose up -d
```

打开 `http://127.0.0.1:8765`。数据保存在名为 `easyread-data` 的 Docker volume 中，包括配置、API Key、日志、原始 PDF、译文和笔记。

指定版本或宿主机端口：

```bash
EASYREAD_IMAGE=tropicalalgae/easyread:1.4.7 EASYREAD_PORT=8876 docker compose up -d
```

更新由容器管理，而不是 EasyRead 桌面版的应用内更新完成：

```bash
docker compose pull
docker compose up -d
```

后台翻译任务的状态会写入文献库；容器重启后，普通导入和翻译任务会按现有任务恢复机制继续处理。

## 数据、备份与额外挂载

容器固定使用 `/data` 作为 `EASYREAD_HOME`，默认文献库是 `/data/library`。不要再设置 `EASYREAD_LIBRARY`：该变量在 EasyRead 中表示测试或临时文献库，会限制文献库迁移功能。

需要批量导入宿主机文件夹时，把它只读挂载到容器，再在页面中填写容器内路径：

```yaml
services:
  easyread:
    volumes:
      - easyread-data:/data
      - /srv/papers:/imports:ro
```

页面中的“选择文件夹”在无桌面环境时会退化为手动填写路径；“打开文件夹”无法打开宿主机的文件管理器。

备份前建议先停止服务，以获得跨多个 JSON 文件一致的快照：

```bash
docker compose stop
docker run --rm -v easyread_easyread-data:/data -v "$PWD":/backup alpine \
  tar czf /backup/easyread-data.tar.gz -C /data .
docker compose start
```

Compose 项目名或 volume 名改过时，请用 `docker volume ls` 确认实际名称。

## 网络与安全

EasyRead 本身没有账号登录功能。任何能够访问页面的人都能读取文献、取得页面写操作 token、修改文献库并使用已配置的模型额度。`config.json` 中还保存模型 API Key，因此不要把容器端口直接暴露到公网。

推荐选择以下方式之一：

- 保持默认的 `127.0.0.1:8765`，通过 SSH 端口转发访问。
- 在同一台主机上使用带身份认证的 Caddy、Nginx、Traefik、Authelia 或 oauth2-proxy。
- 只在受信任的私有网络中，将 `EASYREAD_BIND` 显式设置为需要的宿主机地址。

反向代理必须：

- 保留原始 `Host` 请求头。
- 支持 `/api/presence` 的 WebSocket 升级。
- 允许至少 200 MB 的请求体。
- 为 AI 流式回答设置足够长的读取超时，并关闭响应缓冲。
- 把 EasyRead 放在域名根路径；当前前端不支持 `/easyread/` 这样的子路径部署。

HTTPS 页面会自动使用 `wss://` 连接 presence WebSocket。

## 模型服务

基础镜像不包含 Claude Code、Codex CLI、其他 Agent CLI 或 BabelDOC，推荐使用设置页中的 OpenAI 兼容 API。

同一个 Compose 网络中的 Ollama 可以填写：

```text
http://ollama:11434/v1
```

访问 Linux 宿主机上的 Ollama 可以填写：

```text
http://host.docker.internal:11434/v1
```

`compose.yaml` 已添加 `host.docker.internal:host-gateway`。Ollama 本身还必须监听容器能够访问的地址；只监听宿主机 `127.0.0.1` 时容器仍然无法连接。

## 本地构建

```bash
docker build -t easyread:local .
EASYREAD_IMAGE=easyread:local docker compose up -d
```

镜像使用非 root 用户（UID/GID `10001`）运行。改用宿主机 bind mount 保存 `/data` 时，需要让该用户拥有写权限。

EasyRead 的文献库是文件目录，不是支持并发写入的数据库。只运行一个容器副本，不要让多个容器共享同一个 `/data`。

## Docker Hub 发布流水线

`.github/workflows/docker-publish.yml` 只支持从 Actions 页面手动触发，并且只有默认的 `main` 分支会进入发布阶段。先在 GitHub 仓库的 `release` Environment 中配置两个 Environment secrets：

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

流水线会验证 `pyproject.toml`、`easyread/__init__.py`、`package.json` 和 `package-lock.json` 的版本一致，构建临时镜像并完成 HTTP、持久化写入和 PDF 渲染冒烟测试，然后发布：

```text
<DOCKERHUB_USERNAME>/easyread:<源码版本>
<DOCKERHUB_USERNAME>/easyread:latest
```

流水线不修改版本文件，不创建 Git tag，也不创建 GitHub Release。合并上游后，在 `main` 分支手动运行 `Publish Docker Image` 即可。
