<template>

  <div>

    <el-table :data="data.list" border>
      <el-table-column prop="id" label="申请编号" width="85" />
      <el-table-column prop="data_alias" label="数据名称" width="85"/>
      <el-table-column prop="data_id" label="矢量数据编号" width="110"/>
      <el-table-column prop="applicant_user_number" label="申请人编号" width="100"/>
      <el-table-column prop="applicant_name" label="申请人姓名" width="100"/>
      <el-table-column prop="reason" label="申请理由" />

      <el-table-column label="操作" width="145">
        <template #default="scope">
          <el-button size="small" type="primary" @click="pass(scope.row)">通过</el-button>
          <el-button size="small"  @click="fail(scope.row)">不通过</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>

  <div>

    <el-pagination
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      layout="prev, pager, next, jumper, total"
      @current-change="pageChanged"
      class="view-pagination"

    />

  </div>

</template>

<script setup>
import {reactive, onMounted, ref, computed, watch} from "vue";
import {ElMessage, ElMessageBox} from "element-plus";
// import {useRouter} from "vue-router";
import axios from "axios";
import {useUserStore} from "@/stores/userStore.js";

const basic_url=import.meta.env.VITE_API_URL


// const router=useRouter()

const userStore = useUserStore();
const userNumber = computed(() => userStore.userNumber);
const userName = computed(() => userStore.userName);


const data=reactive({
  list:[]
})
const keyword = ref('');
const page = ref();
const pageSize = ref(2);
const total = ref(0);
const pageChanged = (newPage) => {
  page.value = newPage;
};
watch(page, (newValue, oldValue) => {
    //console.log("oldValue", oldValue, "newValue", newValue)

    if (oldValue !== newValue) {
        if (userNumber.value==='adm1')
        {
          admin1_get_applications()
        }
        else if (userNumber.value==='adm2')
        {
          admin2_get_applications()
        }
    }
})


// admin1_get_applications
const admin1_get_applications = async () => {
  try {
    const response = await axios.get(`${basic_url}/api/adm1_get_applications`, {
      params: { page: page.value, pageSize: pageSize.value }
    });
    if (response.data == null) {
      data.list = [];
      total.value = 0;
      return;
    }
    if (!response.data.status) {
      ElMessage.error(response.data.msg);
      return;
    }
    data.list = response.data.application_data;
    total.value = response.data.pages.total;  // 使用分页数据中的 total
  } catch (err) {
    console.error('Error:', err);
    ElMessage.error('获取记录失败');
  }
};

// admin2_get_applications
const admin2_get_applications = async () => {
  try {
    const response = await axios.get(`${basic_url}/api/adm2_get_applications`, {
      params: { page: page.value, pageSize: pageSize.value }
    });

    if (response.data == null) {
      data.list = [];
      total.value = 0;
      return;
    }

    if (!response.data.status) {
      ElMessage.error(response.data.msg);
      return;
    }

    data.list = response.data.application_data;
    total.value = response.data.pages.total;  // 使用分页数据中的 total

  } catch (err) {
    console.error('Error:', err);
    ElMessage.error('获取记录失败');
  }
};


//分角色请求

onMounted(() => {
  if (userNumber.value==='adm1'){
    admin1_get_applications()
  }else if (userNumber.value==='adm2'){
    admin2_get_applications()
  }
})

const pass = async (row) => {
  try {
    await ElMessageBox.confirm("确定通过?", '审批', {
      type: 'warning',
      confirmButtonText: '确认',
      cancelButtonText: '取消'
    });

    const data = {
      id: row.id,
      user_name: userName.value,
      user_number: userNumber.value
    };

    let passResult;
    if (userNumber.value === 'adm1') {
      passResult = await axios.post(`${basic_url}/api/adm1_pass`, data);
    } else if (userNumber.value === 'adm2') {
      passResult = await axios.post(`${basic_url}/api/adm2_pass`, data);
    }

    if (!passResult.data.status) {
      ElMessage.error(passResult.data.msg);
      return;
    }

    if (userNumber.value === 'adm1') {
      await admin1_get_applications();
    } else if (userNumber.value === 'adm2') {
      await admin2_get_applications();
    }

  } catch (err) {
    console.log("err:", err);
    ElMessage.error('操作失败');
  }
};

const fail = async (row) => {
  try {
    await ElMessageBox.confirm("确定不通过?", '审批', {
      type: 'warning',
      confirmButtonText: '确认',
      cancelButtonText: '取消'
    });

    const data = {
      id: row.id,
      user_name: userName.value,
      user_number: userNumber.value
    };

    let failResult;
    if (userNumber.value === 'adm1') {
      failResult = await axios.post(`${basic_url}/api/adm1_fail`, data);
    } else if (userNumber.value === 'adm2') {
      failResult = await axios.post(`${basic_url}/api/adm2_fail`, data);
    }

    if (!failResult.data.status) {
      ElMessage.error(failResult.data.msg);
      return;
    }

    if (userNumber.value === 'adm1') {
      await admin1_get_applications();
    } else if (userNumber.value === 'adm2') {
      await admin2_get_applications();
    }

  } catch (err) {
    console.log("err:", err);
    ElMessage.error('操作失败');
  }
};




</script>



<style scoped>

.view-pagination{
  margin-top: 20px;
}

</style>