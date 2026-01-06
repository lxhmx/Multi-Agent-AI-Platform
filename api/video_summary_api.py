"""
视频总结 API
提供视频处理的流式接口，支持下载、分析、生成总结

SSE Event Types:
- platform: 平台识别结果
- video_info: 视频信息 (title, author)
- download_start: 开始下载
- download_progress: 下载进度 (0-100)
- download_complete: 下载完成 (path)
- analyze_start: 开始分析
- analyze_progress: 分析进度 (0-100)
- analyze_complete: 分析完成
- summary: 视频总结内容 (Base64编码)
- error: 错误信息
- done: 处理完成
"""

import json
import base64
import traceback
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

from agents.video_summary_agent.pipeline import VideoPipeline
from agents.video_summary_agent.tools.platform_detector import PlatformDetector
from common.dependencies import get_current_user

router = APIRouter(prefix="/api/video-summary", tags=["视频总结"])


class ProcessRequest(BaseModel):
    """视频处理请求"""
    url: str


def encode_base64(text: str) -> str:
    """将文本编码为Base64"""
    return base64.b64encode(text.encode('utf-8')).decode('ascii')


@router.post("/process")
async def process_video(req: ProcessRequest, user=Depends(get_current_user)):
    """
    处理视频（流式输出）
    
    流程：
    1. 识别平台
    2. 获取视频信息
    3. 下载视频
    4. AI分析内容
    5. 返回总结
    """
    url = req.url.strip()
    
    if not url:
        async def error_gen():
            yield f"event: error\ndata: {json.dumps({'message': '视频地址不能为空'}, ensure_ascii=False)}\n\n"
        return StreamingResponse(error_gen(), media_type="text/event-stream")
    
    async def generate():
        pipeline = VideoPipeline()
        detector = PlatformDetector()
        
        try:
            # Step 1: 平台识别
            print(f"\n[Video Summary] ========== 开始处理视频 ==========")
            print(f"[Video Summary] 视频URL: {url}")
            print(f"[Video Summary] Step 1: 识别平台...")
            
            platform = detector.detect(url)
            if not platform:
                supported = ', '.join(detector.get_supported_platforms())
                print(f"[Video Summary] ❌ 不支持的平台")
                yield f"event: error\ndata: {json.dumps({'message': f'不支持的平台，目前支持: {supported}'}, ensure_ascii=False)}\n\n"
                return
            
            print(f"[Video Summary] ✓ 识别到平台: {platform.display_name}")
            yield f"event: platform\ndata: {platform.display_name}\n\n"
            
            # Step 2: 获取视频信息
            print(f"[Video Summary] Step 2: 获取视频信息...")
            video_info = await platform.get_video_info(url)
            
            if not video_info.real_url:
                print(f"[Video Summary] ❌ 无法获取视频地址")
                yield f"event: error\ndata: {json.dumps({'message': '无法获取视频地址'}, ensure_ascii=False)}\n\n"
                return
            
            print(f"[Video Summary] ✓ 视频标题: {video_info.title or '未知'}")
            print(f"[Video Summary] ✓ 视频作者: {video_info.author or '未知'}")
            print(f"[Video Summary] ✓ 视频ID: {video_info.video_id or '未知'}")
            
            info_data = json.dumps({
                'title': video_info.title or '',
                'author': video_info.author or '',
                'video_id': video_info.video_id or ''
            }, ensure_ascii=False)
            yield f"event: video_info\ndata: {info_data}\n\n"
            
            # Step 3: 下载视频
            print(f"[Video Summary] Step 3: 下载视频...")
            yield f"event: download_start\ndata: 1\n\n"
            yield f"event: download_progress\ndata: 30\n\n"
            
            local_path = await pipeline.downloader.download(
                url=video_info.real_url,
                platform=platform.name,
                video_id=video_info.video_id,
                title=video_info.title,
            )
            
            print(f"[Video Summary] ✓ 视频下载完成: {local_path}")
            yield f"event: download_progress\ndata: 100\n\n"
            download_data = json.dumps({'path': local_path}, ensure_ascii=False)
            yield f"event: download_complete\ndata: {download_data}\n\n"
            
            # Step 4: AI分析
            print(f"[Video Summary] Step 4: AI分析视频内容...")
            yield f"event: analyze_start\ndata: 1\n\n"
            yield f"event: analyze_progress\ndata: 30\n\n"
            
            summary = await pipeline.analyzer.analyze(local_path)
            
            print(f"[Video Summary] ✓ AI分析完成，总结长度: {len(summary)} 字符")
            yield f"event: analyze_progress\ndata: 100\n\n"
            yield f"event: analyze_complete\ndata: 1\n\n"
            
            # Step 5: 返回总结
            print(f"[Video Summary] Step 5: 返回总结内容...")
            summary_encoded = encode_base64(summary)
            yield f"event: summary\ndata: {summary_encoded}\n\n"
            
            # 完成
            print(f"[Video Summary] ========== 处理完成 ==========\n")
            yield f"event: done\ndata: {json.dumps({'success': True}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            print(f"[Video Summary] ❌ 处理失败: {traceback.format_exc()}")
            yield f"event: error\ndata: {json.dumps({'message': str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


@router.get("/play")
async def play_video(
    path: str = Query(..., description="视频文件路径"),
    user=Depends(get_current_user)
):
    """
    播放视频文件
    
    返回视频文件流，支持浏览器播放
    """
    # 安全检查：确保路径在允许的目录内
    video_path = Path(path)
    
    # 检查文件是否存在
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="视频文件不存在")
    
    # 检查是否是视频文件
    allowed_extensions = {'.mp4', '.webm', '.mov', '.avi', '.mkv'}
    if video_path.suffix.lower() not in allowed_extensions:
        raise HTTPException(status_code=400, detail="不支持的视频格式")
    
    # 获取MIME类型
    mime_types = {
        '.mp4': 'video/mp4',
        '.webm': 'video/webm',
        '.mov': 'video/quicktime',
        '.avi': 'video/x-msvideo',
        '.mkv': 'video/x-matroska'
    }
    media_type = mime_types.get(video_path.suffix.lower(), 'video/mp4')
    
    return FileResponse(
        path=str(video_path),
        media_type=media_type,
        filename=video_path.name
    )
