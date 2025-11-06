import { ref, onMounted } from 'vue';
import api from '@/utils/api';

export function useAuth() {
  const isAdmin = ref(false);
  const currentUser = ref<any>(null);
  const loading = ref(true);

  const loadUserInfo = async () => {
    try {
      const user = await api.get('/api/users/me');
      currentUser.value = user;
      isAdmin.value = user.is_superuser;
    } catch (error) {
      console.error('Failed to load user info:', error);
    } finally {
      loading.value = false;
    }
  };

  onMounted(() => {
    loadUserInfo();
  });

  return {
    isAdmin,
    currentUser,
    loading,
    loadUserInfo,
  };
}
