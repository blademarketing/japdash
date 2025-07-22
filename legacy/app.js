let services = [];
let selectedService = null;

const searchInput = document.getElementById('service-search');
const serviceList = document.getElementById('service-list');
const selectedServiceId = document.getElementById('selected-service-id');
const selectedServiceInfo = document.getElementById('selected-service-info');

fetch('/jap/services')
    .then(res => res.json())
    .then(data => {
        services = data;
        searchInput.addEventListener('input', () => renderList(searchInput.value.toLowerCase()));
        searchInput.addEventListener('focus', () => serviceList.classList.remove('hidden'));
        document.addEventListener('click', (e) => {
            if (!searchInput.contains(e.target) && !serviceList.contains(e.target)) {
                serviceList.classList.add('hidden');
            }
        });
    });

function renderList(filter) {
    serviceList.innerHTML = '';

    services
        .filter(s => s.name.toLowerCase().includes(filter))
        .forEach(service => {
            const li = document.createElement('li');
            li.textContent = `${service.service} - ${service.name}`;
            li.className = 'p-2 hover:bg-gray-100 cursor-pointer';

            li.addEventListener('click', () => {
                selectedService = service;
                searchInput.value = `${service.service} - ${service.name}`;
                selectedServiceId.value = service.service;
                selectedServiceInfo.textContent = `Selected: ${service.name} (${service.type})`;
                serviceList.classList.add('hidden');

                // 👇 Render inputs from /form-fields/{type}
                fetch(`/jap/form-fields/${encodeURIComponent(service.type)}?service_name=${encodeURIComponent(service.name)}`)
                    .then(res => res.json())
                    .then(fields => {
                        const container = document.getElementById('dynamic-fields');
                        const form = document.getElementById('order-form');
                        const responseBox = document.getElementById('order-response');

                        container.innerHTML = '';
                        responseBox.textContent = '';

                        if (fields.length === 0) {
                            container.innerHTML = `<p class="text-red-600">This service type <strong>${service.type}</strong> is not yet supported.</p>`;
                            form.classList.remove('hidden');
                            form.querySelector('button[type="submit"]').classList.add('hidden');
                            return;
                        }

                        form.querySelector('button[type="submit"]').classList.remove('hidden');

                        fields.forEach(field => {
                            const wrapper = document.createElement('div');
                            wrapper.className = 'relative';

                            const label = document.createElement('label');
                            label.textContent = field.title;
                            label.className = 'block font-medium';

                            let input;
                            if (field.type === 'textarea') {
                                input = document.createElement('textarea');
                                input.rows = 4;
                            } else {
                                input = document.createElement('input');
                                input.type = field.type;
                            }

                            input.name = field.name;
                            input.className = 'border p-2 w-full rounded mt-1';

                            wrapper.appendChild(label);
                            wrapper.appendChild(input);

                            if ('ai' in field) {
                                const button = document.createElement('button');
                                button.type = 'button';
                                button.textContent = '🤖';
                                button.title = 'Generate with AI';
                                button.className = 'absolute right-2 top-8 text-lg hover:scale-110';
                                button.onclick = async () => {
                                    const allInputs = document.querySelectorAll('#order-form input, #order-form textarea');
                                    const formData = {};

                                    allInputs.forEach(el => {
                                        if (el.name) {
                                            if (el.type === 'checkbox') {
                                                formData[el.name] = el.checked ? 'yes' : 'no'; // <-- fix here
                                            } else {
                                                formData[el.name] = el.value;
                                            }
                                        }
                                    });


                                    const res = await fetch('/jap/ai-generate', {
                                        method: 'POST',
                                        headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({
                                            ai: field.ai,
                                            target_field: field.name,
                                            form_data: formData
                                        })
                                    });

                                    const result = await res.json();
                                    if (result.value) {
                                        const target = document.querySelector(`[name="${result.field}"]`);
                                        if (target) target.value = result.value;
                                    } else {
                                        alert("AI generation failed.");
                                    }
                                };

                                wrapper.appendChild(button);
                            }

                            if (field.subtext) {
                                const sub = document.createElement('p');
                                sub.textContent = field.subtext;
                                sub.className = 'text-xs text-gray-500 mt-1';
                                wrapper.appendChild(sub);
                            }

                            input.dataset.submit = field.submit ? 'true' : 'false';
                            container.appendChild(wrapper);
                        });

                        form.classList.remove('hidden');
                    });
            });

            serviceList.appendChild(li);
        });

    serviceList.classList.toggle('hidden', serviceList.children.length === 0);
}



document.getElementById('order-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = { service: document.getElementById('selected-service-id').value };
    const form = e.target;
    const fields = form.querySelectorAll('input, textarea');
    fields.forEach(input => {
        if (input.name && input.dataset.submit === 'true' && input.value) {
            data[input.name] = input.value;
        }
    });


    const res = await fetch('/jap/order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    const result = await res.json();
    document.getElementById('order-response').textContent = JSON.stringify(result, null, 2);
});

