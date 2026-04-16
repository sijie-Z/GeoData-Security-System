<template>
  <div class="employee-help-page page-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>系统帮助</span>
        </div>
      </template>
      <div class="help-content">
        <h2>欢迎使用数据管理系统！</h2>
        <p>本系统旨在帮助您高效地管理和使用各类数据资源。以下是一些常见功能的使用指南：</p>
 
        <h3>1. 数据目录检索</h3>
        <p>在“数据目录检索”页面，您可以浏览系统内所有可用的矢量数据和普通图像数据。使用顶部的搜索框可以根据数据名称、标识或来源进行快速查找。您还可以根据数据类型（矢量/图像）切换查看不同的数据集。</p>
        <p>点击数据条目右侧的“查看详情”按钮，可以预览数据内容（矢量数据会显示地图预览，图像数据会显示图片预览）并查看详细元数据。如果您对某个数据感兴趣，可以点击“申请数据”按钮提交数据申请。</p>
 
        <h3>2. 我的申请记录</h3>
        <p>“我的申请记录”页面展示了您所有提交的数据申请的状态。您可以看到每个申请的审批进度（一审、二审），以及审批结果。请耐心等待审批完成。</p>
 
        <h3>3. 已批准数据下载</h3>
        <p>当您的数据申请获得批准后，该数据会出现在“已批准数据下载”页面。您可以直接点击相应的“下载数据”按钮，将批准的数据文件下载到本地。请注意，只有获得最终批准的数据才可下载。</p>
 
        <h3>4. 个人中心</h3>
        <p>点击页面右上角的头像，选择“个人中心”，您可以查看和管理您的个人信息，例如姓名、员工编号、部门等。未来这里将支持编辑资料和修改密码等功能。</p>
 
        <h3>5. 关于系统</h3>
        <p>“关于系统”页面提供了系统的基本信息，包括版本号、开发团队等，让您对本系统有更全面的了解。</p>
 
        <el-divider />
 
        <p>如果您在使用过程中遇到任何问题，或有任何建议，请随时联系系统管理员。</p>
        <p>感谢您的使用！</p>
      </div>
    </el-card>
  </div>
</template>
 
<script setup>
import { ElDivider } from 'element-plus';
</script>
 
<style scoped>
.employee-help-page {
  padding: 24px;
  background-color: #f7f8fa;
  min-height: calc(100vh - 60px - 40px);
  display: flex;
  justify-content: center;
  align-items: flex-start;
}
 
.box-card {
  width: 100%;
  max-width: 900px;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0,0,0,.04);
}
 
.card-header {
  font-size: 20px;
  font-weight: 600;
  color: #333;
}
 
.help-content {
  padding: 20px;
  line-height: 1.8;
  color: #4b5563;
}
 
.help-content h2, .help-content h3 {
  color: #1d2129;
  margin-top: 25px;
  margin-bottom: 15px;
}
 
.help-content h2 {
  font-size: 24px;
  font-weight: 700;
}
 
.help-content h3 {
  font-size: 18px;
  font-weight: 600;
  border-bottom: 1px solid #eee;
  padding-bottom: 5px;
  margin-bottom: 15px;
}
 
.help-content p {
  margin-bottom: 10px;
}
 
.help-content ul {
  list-style-type: disc;
  margin-left: 20px;
  margin-bottom: 10px;
}
 
.help-content li {
  margin-bottom: 5px;
}
</style>
