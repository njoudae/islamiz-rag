<script setup>
import { Head, Link, useForm } from '@inertiajs/vue3';
import { ref } from 'vue';
import Icon from '../../components/Icon.vue';
import Logo from '../../components/Logo.vue';
import PublicLayout from '../../layouts/PublicLayout.vue';
import { toast } from '../../lib/ui.js';

defineOptions({ layout: PublicLayout });

const props = defineProps({
    fromAdmin: { type: Boolean, default: false },
    demoCredentials: { type: Object, default: null },
});

const form = useForm({ email: '', password: '', remember: true });
const clientErrors = ref({});
const showPassword = ref(false);

function validate() {
    const email = form.email.trim();
    const errors = {};
    if (!email) errors.email = 'أدخل بريدك الإلكتروني.';
    else if (!/^\S+@\S+\.\S+$/.test(email)) errors.email = 'صيغة البريد غير صحيحة، مثل name@example.com.';
    if (!form.password) errors.password = 'أدخل كلمة المرور.';
    clientErrors.value = errors;
    return Object.keys(errors).length === 0;
}

function submit() {
    if (!validate()) return;
    form.post('/login', { onFinish: () => form.reset('password') });
}

function fillDemo() {
    form.email = props.demoCredentials.email;
    form.password = props.demoCredentials.password;
    clientErrors.value = {};
    form.clearErrors();
}

// The server reports wrong credentials on "email"; the design shows that message under the password.
const emailError = () => clientErrors.value.email || (form.errors.email && form.errors.email !== 'بيانات الدخول غير صحيحة.' ? form.errors.email : '');
const passwordError = () =>
    clientErrors.value.password || form.errors.password || (form.errors.email === 'بيانات الدخول غير صحيحة.' ? 'البريد أو كلمة المرور غير صحيحة.' : '');
</script>

<template>
    <Head title="دخول المشرفين" />

    <div class="wrap login-wrap">
        <div class="login">
            <Link class="brand" href="/" style="align-self: center"><Logo /><span>دليل</span></Link>

            <div v-if="fromAdmin" class="alert">
                <Icon name="lock" /><span class="alert-title">لوحة الإدارة للمشرفين فقط</span><span class="alert-desc">سجّل الدخول لمتابعة أداء النموذج ومراجعة الأسئلة.</span>
            </div>

            <div class="card">
                <div>
                    <h1 class="card-title" style="font-size: 1.125rem">تسجيل الدخول</h1>
                    <p class="card-desc">لوحة الإدارة لفريق المراجعة الشرعية والتقنية.</p>
                </div>
                <form novalidate style="display: flex; flex-direction: column; gap: 16px" @submit.prevent="submit">
                    <div class="field">
                        <label class="label" for="email">البريد الإلكتروني</label>
                        <input
                            id="email"
                            v-model="form.email"
                            class="input"
                            type="email"
                            dir="ltr"
                            placeholder="name@example.com"
                            autocomplete="username"
                            :aria-invalid="emailError() ? 'true' : undefined"
                            aria-describedby="emailErr"
                            @input="clientErrors.email = ''"
                        />
                        <span v-if="emailError()" id="emailErr" class="err">{{ emailError() }}</span>
                    </div>
                    <div class="field">
                        <div style="display: flex; justify-content: space-between; align-items: center">
                            <label class="label" for="pass">كلمة المرور</label>
                            <!-- Dummy: there is no password-reset flow; the account is managed through configuration. -->
                            <button type="button" class="act-link muted" @click="toast('استعادة كلمة المرور غير مفعّلة بعد. استخدم حساب المشرف المعروض أدناه.', 'mail')">نسيت كلمة المرور؟</button>
                        </div>
                        <div class="pw">
                            <input
                                id="pass"
                                v-model="form.password"
                                class="input"
                                :type="showPassword ? 'text' : 'password'"
                                dir="ltr"
                                autocomplete="current-password"
                                :aria-invalid="passwordError() ? 'true' : undefined"
                                aria-describedby="passErr"
                                @input="clientErrors.password = ''"
                            />
                            <button type="button" class="icon-btn" :aria-label="showPassword ? 'إخفاء كلمة المرور' : 'إظهار كلمة المرور'" @click="showPassword = !showPassword">
                                <Icon :name="showPassword ? 'lock' : 'eye'" />
                            </button>
                        </div>
                        <span v-if="passwordError()" id="passErr" class="err" role="alert">{{ passwordError() }}</span>
                    </div>
                    <label class="check"><input v-model="form.remember" type="checkbox" />تذكّرني على هذا الجهاز</label>
                    <button class="btn btn-block btn-lg" type="submit" :disabled="form.processing">{{ form.processing ? 'جارٍ الدخول…' : 'دخول' }}</button>
                </form>
                <div v-if="demoCredentials" class="demo-cred">
                    <Icon name="key-round" />
                    <span style="flex: 1; min-width: 180px">حساب المشرف: <code>{{ demoCredentials.email }}</code> · <code>{{ demoCredentials.password }}</code></span>
                    <button class="btn btn-secondary btn-xs" type="button" @click="fillDemo">تعبئة</button>
                </div>
            </div>
            <p class="help" style="text-align: center; line-height: 1.7">الدخول مخصص لفريق المشرفين. يستخدم زوار الموقع الأداة دون تسجيل.</p>
        </div>
    </div>
</template>
