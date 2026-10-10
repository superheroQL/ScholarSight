<template>
  <div class="my-container">
    <van-nav-bar :title="$t('my.title')" fixed />

    <div class="page-shell">
      <!-- 用户卡片 -->
      <section class="user-card" @click="goToProfile" v-if="isLogin">
        <div class="avatar">
          <van-image
            round
            width="64"
            height="64"
            src="https://fastly.jsdelivr.net/npm/@vant/assets/cat.jpeg"
          />
        </div>
        <div class="user-meta">
          <div class="username">{{ userInfo.username }}</div>
          <div class="desc">{{ userBio || $t('profile.bio') }}</div>
        </div>
        <van-icon name="arrow" class="arrow-icon" />
      </section>

      <section class="user-card" v-else>
        <div class="avatar">
          <van-image
            round
            width="64"
            height="64"
            src="https://fastly.jsdelivr.net/npm/@vant/assets/cat.jpeg"
          />
        </div>
        <div class="user-meta">
          <div class="username">{{ $t('my.notLoggedIn') }}</div>
          <div class="desc">
            <button class="btn-primary" @click="goToLogin">{{ $t('my.goToLogin') }}</button>
            <button class="btn-plain" @click="goToRegister">{{ $t('my.goToRegister') }}</button>
          </div>
        </div>
      </section>

      <!-- 菜单卡片 -->
      <section class="menu-card">
        <div class="menu-row" @click="goToFavorite">
          <van-icon name="star-o" class="menu-icon" />
          <span class="menu-label">{{ $t('my.myFavorite') }}</span>
          <van-icon name="arrow" class="row-arrow" />
        </div>
        <div class="menu-row" @click="goToHistory">
          <van-icon name="clock-o" class="menu-icon" />
          <span class="menu-label">{{ $t('my.browsingHistory') }}</span>
          <van-icon name="arrow" class="row-arrow" />
        </div>
        <div class="menu-row">
          <van-icon name="bell-o" class="menu-icon" />
          <span class="menu-label">{{ $t('my.notifications') }}</span>
          <van-icon name="arrow" class="row-arrow" />
        </div>
        <div class="menu-row" @click="goToSettings">
          <van-icon name="setting-o" class="menu-icon" />
          <span class="menu-label">{{ $t('my.settings') }}</span>
          <van-icon name="arrow" class="row-arrow" />
        </div>
      </section>

      <section class="menu-card" v-if="isLogin">
        <div class="menu-row logout" @click="handleLogout">
          <van-icon name="cross" class="menu-icon" />
          <span class="menu-label">{{ $t('my.logout') }}</span>
        </div>
      </section>
    </div>

    <tab-bar />
  </div>
</template>

<script setup>
import { onMounted } from 'vue';
import { useUserStore } from '../store/user';
import { useRouter } from 'vue-router';
import { computed, ref } from 'vue';
import { showDialog, showToast } from 'vant';
import TabBar from '../components/TabBar.vue';
import { useI18n } from 'vue-i18n';

const userStore = useUserStore();
const router = useRouter();
const { t } = useI18n();

// 从store获取用户信息和登录状态
const userInfo = computed(() => userStore.userInfo);
const isLogin = computed(() => userStore.getLoginStatus);
const userBio = computed(() => userStore.getUserBio || t('profile.bio'));

// 跳转到登录页
const goToLogin = () => {
  router.push('/login');
};

// 跳转到注册页
const goToRegister = () => {
  router.push('/register');
};

// 跳转到个人信息页
const goToProfile = () => {
  if (isLogin.value) {
    router.push('/profile');
  }
};

// 跳转到浏览历史页面
const goToHistory = () => {
  if (isLogin.value) {
    router.push('/history');
  } else {
    showToast(t('common.login'));
    router.push('/login');
  }
};

// 跳转到我的收藏页面
const goToFavorite = () => {
  if (isLogin.value) {
    router.push('/favorite');
  } else {
    showToast(t('common.login'));
    router.push('/login');
  }
};

// 跳转到设置页面
const goToSettings = () => {
  router.push('/settings');
};

// 退出登录
const handleLogout = () => {
  showDialog({
    title: t('common.confirm'),
    message: t('my.logout') + '?',
    showCancelButton: true,
  }).then((action) => {
    if (action === 'confirm') {
      userStore.logout();
      router.push('/login');
    }
  });
};

// 获取用户信息
onMounted(async () => {
  try {
    await userStore.getUserInfoDetail();
  } catch (error) {
    console.error('获取用户信息失败:', error);
  }
});
</script>

<style scoped>
.my-container {
  min-height: 100vh;
  padding-top: 46px;
  padding-bottom: 60px;
  background: linear-gradient(180deg, #f4f7ff 0%, #f7f8fa 100%);
  box-sizing: border-box;
}

.page-shell {
  width: min(640px, 100%);
  margin: 0 auto;
  padding: 16px;
  box-sizing: border-box;
}

/* 统一卡片样式（与主题一致） */
.user-card,
.menu-card {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
}

/* 用户卡片 */
.user-card {
  display: flex;
  align-items: center;
  padding: 20px 18px;
  margin-bottom: 14px;
  position: relative;
  cursor: pointer;
}

.avatar {
  margin-right: 14px;
  flex-shrink: 0;
}

.user-meta {
  flex: 1;
  min-width: 0;
}

.username {
  font-size: 19px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 5px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.desc {
  font-size: 13px;
  color: #94a3b8;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.arrow-icon {
  color: #cbd5e1;
  font-size: 16px;
}

/* 未登录按钮 */
.btn-primary {
  border: none;
  border-radius: 10px;
  padding: 7px 16px;
  margin-right: 10px;
  color: #fff;
  background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%);
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  font-weight: 600;
}

.btn-plain {
  border: 1px solid #dbe5f0;
  border-radius: 10px;
  padding: 7px 16px;
  color: #24528a;
  background: #fff;
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  font-weight: 600;
}

/* 菜单卡片 */
.menu-card {
  margin-bottom: 14px;
  padding: 4px 8px;
}

.menu-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 12px;
  cursor: pointer;
}

.menu-row + .menu-row {
  border-top: 1px solid #f1f5f9;
}

.menu-row:hover {
  background: #f8fafc;
}

.menu-icon {
  color: #4f46e5;
  font-size: 18px;
}

.menu-label {
  flex: 1;
  color: #334155;
  font-size: 14px;
}

.row-arrow {
  color: #cbd5e1;
  font-size: 14px;
}

.logout .menu-icon,
.logout .menu-label {
  color: #ef4444;
}
</style>
