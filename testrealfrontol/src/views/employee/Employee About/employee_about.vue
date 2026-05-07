<template>
  <div class="employee-about-page page-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>关于系统</span>
        </div>
      </template>
      <div class="about-content">
        <h2>空间数据追踪系统</h2>
        <p><strong>版本：</strong> v1.0</p>
        <p><strong>发布日期：</strong> 2025</p>

        <el-divider />

        <h3>系统简介</h3>
        <p>本系统是面向地理空间数据（矢量与栅格）的一体化管理与追踪平台。支持员工端的数据目录检索、数据申请、已批准数据下载、操作历史与站内通知；支持管理员端的双级审批、水印生成/嵌入/提取、系统公告与定向通知、系统操作日志及数据上传等，实现从申请到下载的全流程可追溯与水印保护。</p>

        <h3>主要功能</h3>
        <ul>
          <li><strong>数据目录：</strong> 矢量与栅格数据的检索与浏览；列表缩略图与地图瓦片预览。</li>
          <li><strong>数据申请与审批：</strong> 员工提交申请，管理员一审、二审；支持矢量与栅格分别审批。</li>
          <li><strong>水印全流程：</strong> 二维码水印生成（可写申请原因、备注及精度参数）、矢量/栅格水印嵌入与提取。</li>
          <li><strong>下载与追踪：</strong> 仅已批准且完成水印嵌入的数据可下载；下载行为可记录。</li>
          <li><strong>站内通知：</strong> 管理员可向指定用户或全体员工发送通知；员工可查看并标记已读。</li>
          <li><strong>日志与历史：</strong> 管理员可查看全部操作日志并按用户编号、姓名、操作类型筛选；员工可查看本人操作历史。</li>
          <li><strong>个人中心：</strong> 查看与维护个人信息、修改密码等。</li>
        </ul>

        <h3>技术说明</h3>
        <p>前端：Vue 3、Vite、Element Plus、Pinia；地图与栅格展示采用瓦片服务按需加载。后端：Flask、Flask-RESTful、JWT 认证；栅格展示采用 rasterio 等生成瓦片。数据存储使用 MySQL。</p>

        <el-divider />

        <p>感谢使用本系统。如有问题或建议，请联系系统管理员。</p>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ElDivider } from 'element-plus';
</script>

<style scoped>
.employee-about-page {
  padding: 24px;
  background-color: #f7f8fa;
  min-height: calc(100vh - 60px - 40px);
  display: flex;
  justify-content: center;
  align-items: flex-start;
}

.box-card {
  width: 100%;
  max-width: 800px;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0,0,0,.04);
}

.card-header {
  font-size: 20px;
  font-weight: 600;
  color: #333;
}

.about-content {
  padding: 20px;
  line-height: 1.8;
  color: #4b5563;
}

.about-content h2 {
  font-size: 24px;
  font-weight: 700;
  color: #1d2129;
  margin-top: 15px;
  margin-bottom: 20px;
}

.about-content h3 {
  font-size: 18px;
  font-weight: 600;
  color: #1d2129;
  margin-top: 25px;
  margin-bottom: 15px;
  border-bottom: 1px solid #eee;
  padding-bottom: 5px;
}

.about-content p {
  margin-bottom: 10px;
}

.about-content ul {
  list-style-type: disc;
  margin-left: 20px;
  margin-bottom: 10px;
}

.about-content li {
  margin-bottom: 5px;
}
</style>
