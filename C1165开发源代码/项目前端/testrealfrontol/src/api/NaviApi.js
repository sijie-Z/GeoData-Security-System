import Axios from "@/utils/Axios.js"


const getAdmById=(id)=>{
    return Axios.get(`/api/admin/nav/getById?id=${id}`)
}

const getAdmListByParentId = (parent_id) => {
    return Axios.get(`/api/admin/nav/getListByParentId?parent_id=${parent_id}`)
}


const getAdmAllById = (id) => {
    return Axios.get(`/api/admin/nav/list?id=${id}`)
}

const getAdmAll = () => {
  return Axios.get('/api/admin/nav/tree').then(response => {
    if (response.data.status) {
      return response.data.data;  // 直接返回导航树数组
    } else {
      throw new Error(response.data.msg);
    }
  });
}

const getEmpById=(id)=>{
    return Axios.get(`/api/employee/nav/getById?id=${id}`)
}

const getEmpListByParentId = (parent_id) => {
    return Axios.get(`/api/employee/nav/getListByParentId?parent_id=${parent_id}`)
}

const getEmpAllById = (id) => {
    return Axios.get(`/api/employee/nav/list?id=${id}`)
}

const getEmpAll = () => {
  return Axios.get('/api/employee/nav/tree').then(response => {
    if (response.data.status) {
      return response.data.data;  // 直接返回导航树数组
    } else {
      throw new Error(response.data.msg);
    }
  });
}

export default { getAdmById,getAdmListByParentId,getAdmAllById,getAdmAll,getEmpById,getEmpListByParentId,getEmpAllById,getEmpAll }
