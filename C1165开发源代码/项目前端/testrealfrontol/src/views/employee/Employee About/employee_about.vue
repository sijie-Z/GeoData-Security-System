<template>
  <div class="employee-about-page page-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>关于系统</span>
        </div>
      </template>
      <div class="about-content">
        <h2>数据管理系统</h2>
        <p><strong>版本:</strong> v1.0.0</p>
        <p><strong>开发团队:</strong> UnityBuilders</p>
        <p><strong>发布日期:</strong> 2025年7月</p>

        <el-divider />

        <h3>核心功能</h3>
        <p>本数据管理系统是一个为内部员工设计的综合性平台，旨在集中管理、分发和使用各类地理空间数据及通用图像数据。通过本系统，员工可以方便地检索所需数据、提交数据申请，并在获得批准后进行下载。</p>
        <p>系统致力于提升数据使用的效率和规范性，确保数据资产的安全与合规，为员工提供一个便捷、高效的数据服务入口。</p>
        <ul>
          <li><strong>数据目录检索:</strong> 全面浏览和搜索矢量数据、普通图像数据。</li>
          <li><strong>数据申请管理:</strong> 提交、跟踪和管理数据申请记录。</li>
          <li><strong>数据下载:</strong> 下载已批准的数据文件。</li>
          <li><strong>个人中心:</strong> 管理个人信息和账户安全。</li>
        </ul>

        <el-divider />

        <p>感谢您使用本系统。我们将持续优化和改进，为您提供更优质的服务。</p>
        <p>如需技术支持，请联系：support@yourcompany.com</p>
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
